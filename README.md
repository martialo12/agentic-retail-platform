# Agentic Retail Platform

A **reusable agentic socle** for retail generative AI on GCP — and two agents that
prove it. The point isn't "one more chatbot"; it's the **foundations**: an agent
registry, an MCP tool layer, identity/policy, LangGraph orchestration, RAG, LLMOps
tracing/eval, and GCP-ready IaC. Adding a new agent is a **registry YAML + a
prompt**, not a rewrite.

> POC destiné à démontrer la capacité à *poser les fondations* d'une plateforme
> agentique multi-cas d'usage. Données 100% synthétiques, jamais de donnée client.
> Déployé sur GCP (Cloud Run, europe-west1) pour la période de démonstration.

## Architecture

```
requête ─▶ Orchestration (LangGraph)
              │  charge AgentSpec ◀── Agent Registry
              │  chaque appel outil ─▶ Policy authorize ─▶ MCP server
              │  retrieve ─▶ RAG retriever ─▶ pgvector / AlloyDB
              │  chaque étape ─▶ trace JSONL (LLMOps)
              ▼
        sortie validée (Pydantic) | escalade humaine
```

| Couche | Rôle |
|---|---|
| Registry | Déclare un agent en YAML (modèle, outils autorisés, escalade, owner) |
| Policy | Autorise/refuse chaque appel d'outil selon le spec de l'agent |
| MCP | Serveur exposant les outils métier ; les agents ne passent que par lui |
| Orchestration | LangGraph `retrieve → draft → self-check → (escalate \| emit)` |
| RAG | pgvector en local, interface SQL compatible AlloyDB en prod |
| LLMOps | Traces JSONL par run + harness d'éval sur golden set |
| IaC | Dockerfile, Terraform (Cloud Run/AlloyDB/GCS/Redis), manifests K8s |

## Les deux agents

- **`product-enricher`** (RAG) — enrichit une fiche produit incomplète en attributs
  structurés validés, avec self-check et escalade humaine.
- **`customer-assistant`** (multi-outils) — répond via outils MCP (`lookup_order`,
  `get_product`, `search_catalog`), sans droit d'écriture. Même socle, nouveau spec.

## Quickstart

```bash
make setup            # uv sync (Python 3.11 auto)
make setup-agents     # deps LLM/RAG/MCP
cp .env.example .env  # configurer le provider (vertex | local)
make up               # postgres+pgvector + redis
make ingest           # embeddings du catalogue synthétique
make eval             # rapport d'évaluation
make test             # suite de tests
```

## Console web

Une surface qui rend la **gouvernance du socle observable** : autorisations,
refus d'outils, escalades et audit, en direct plutôt que dans un fichier de log.
La démo qui compte n'est pas « un agent répond » — c'est *demander un
remboursement et voir le run s'arrêter avant même que le modèle soit appelé*.

| Vue | Ce qu'elle prouve |
|---|---|
| `/` Assistant | chat + bande d'audit live : outils utilisés, refus, escalade |
| `/enrichissement` | avant/après d'une fiche, confiance mesurée contre le seuil |
| `/observabilité` | table de runs filtrable, timeline par run rejouable |

```bash
make serve-api   # API (SSE) sur :8000
make front-dev   # console Vue 3 sur :5173
make up          # ou tout le stack conteneurisé : db + redis + api + front
```

**Script de démo** (dans l'ordre) :

1. `Où en est ma commande o002 ?` — réponse via l'outil `lookup_order` (autorisé) ;
   la bande imprime récupération → appel outil → appel modèle → sortie validée.
2. `Je veux un remboursement pour ma commande o002.` — **escalade avant tout
   appel modèle** : le run est *marqué* et l'interface la présente comme une
   issue, jamais comme une erreur (FR-017).
3. Enrichissement de la fiche `p001` — avant/après, la confiance mesurée affichée
   contre le seuil de la spec : sous le seuil, rien n'est écrit.

> **L'API n'est pas authentifiée** (FR-018). L'IaC porte la contrainte par
> construction plutôt que par avertissement : `ingress` interne et
> `invoker_members` vide sont les valeurs par défaut, si bien qu'ouvrir le
> service demande un geste explicite, tracé dans les variables.
>
> Le déploiement de démonstration pose précisément ce geste : `ingress` ouvert et
> `allUsers` en invoker, pour que la console soit accessible sans compte GCP.
> C'est une exception assumée et temporaire, à refermer à la fin des tests.
> L'authentification reste le seul vrai obstacle entre ce POC et un pilote payant.

**Mesure d'usage.** La console sait remonter une poignée d'événements à GA4
(question posée, enrichissement lancé, escalade affichée puis reprise par un
canal). Rien n'est chargé tant que `GA_MEASUREMENT_ID` est vide : pas de script
tiers, pas de cookie, et c'est l'état par défaut en développement comme en test.
Le contenu tapé par un visiteur ne part jamais dans la mesure, seulement des
catégories. Le consentement démarre refusé (Consent Mode v2).

La définition de *done* du dépôt inclut désormais `make front` (lint +
type-check + build de la console) en plus de `make lint && make test`.

## Infrastructure

```bash
make docker        # image de prod multi-stage, non-root, CMD = serveur MCP
make front-docker  # image nginx du bundle statique de la console
make tf-validate   # tofu init -backend=false + validate + fmt -check
make k8s-validate  # kubeconform strict (aucun cluster requis)
make iac           # les trois d'un coup
```

| Local (`make up`) | GCP (`infra/terraform`) |
|---|---|
| conteneur `pgvector/pgvector:pg16` | Cloud SQL PostgreSQL + `pgvector`, IP privée |
| `logs/runs/*.jsonl` | bucket GCS versionné + rétention |
| `make ingest` | Cloud Run Job, même image, même code |
| `python -m arp.mcp` | Cloud Run v2, direct VPC egress, SA dédié |
| `python -m arp.api` (console) | Cloud Run v2, origines CORS nommées |
| console statique (nginx) | Cloud Run v2, bundle statique, sans secret ni VPC |

Le DSN transite par **Secret Manager**, jamais par une variable d'environnement
en clair, et le mot de passe est masqué dans les journaux. La console ne connaît
pas l'URL de l'API à la compilation : son entrypoint réécrit `/config.js` au
démarrage, pour qu'une même image serve tous les environnements.

Le premier dessin visait AlloyDB et Memorystore. Cloud SQL les remplace parce
que le POC ne demandait ni la capacité ni le prix d'AlloyDB, et Redis a été
retiré faute d'usage réel : le cluster coûtait plus que ce qu'il servait.

**Outils.** `tofu` (OpenTofu) est le défaut ; `export TF=terraform` pour utiliser
Terraform HashiCorp. La validation K8s passe par `kubeconform` en conteneur car
`kubectl --dry-run=client` exige un API server joignable.

**État distant.** L'état reste local, sans bloc `backend` : un seul opérateur,
un seul environnement. C'est à revoir dès qu'une deuxième personne applique.

## LLM provider

Interface **agnostique** : cible prod **Vertex AI Gemini** (leur stack GCP),
fallback local configurable, `FakeProvider` déterministe en test. Swap de provider
= une variable d'env, zéro changement de code métier.

## RAG vs fine-tuning

Position argumentée et **chiffrée** par le harness d'éval, dans
`docs/eval/rag-vs-finetuning.md` (généré en phase 2). En bref : RAG d'abord pour la
fraîcheur catalogue et l'auditabilité ; fine-tuning réservé au style/format une fois
le RAG à son plafond.

## Statut

Phases 0-5 livrées : fondation + spec, socle, `product-enricher`,
`customer-assistant`, IaC GCP, et la **console web** (API SSE + front Vue 3 +
index des runs). Le tout tourne sur Cloud Run en europe-west1 pour la période de
démonstration, avec Gemini 2.5 Flash sur Vertex AI. Détail des tâches dans
`docs/superpowers/plans/2026-07-23-agentic-retail-platform.md` et
`docs/superpowers/plans/2026-07-23-web-console.md`.
