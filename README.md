# Agentic Retail Platform

A **reusable agentic socle** for retail generative AI on GCP — and two agents that
prove it. The point isn't "one more chatbot"; it's the **foundations**: an agent
registry, an MCP tool layer, identity/policy, LangGraph orchestration, RAG, LLMOps
tracing/eval, and GCP-ready IaC. Adding a new agent is a **registry YAML + a
prompt**, not a rewrite.

> POC destiné à démontrer la capacité à *poser les fondations* d'une plateforme
> agentique multi-cas d'usage. Données 100% synthétiques ; aucun déploiement réel
> (l'IaC est écrite et validée, pas déployée).

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

> **L'API est délibérément non authentifiée** (FR-018) et ne doit **jamais** être
> exposée. L'IaC porte cette contrainte par construction — ingress interne et
> `invoker_members` vide — plutôt qu'un avertissement : accorder un invoker est
> l'acte délibéré qui doit attendre l'authentification.

La définition de *done* du dépôt inclut désormais `make front` (lint +
type-check + build de la console) en plus de `make lint && make test`.

## Infrastructure (écrite et validée, non déployée)

```bash
make docker        # image de prod multi-stage, non-root, CMD = serveur MCP
make front-docker  # image nginx du bundle statique de la console
make tf-validate   # tofu init -backend=false + validate + fmt -check
make k8s-validate  # kubeconform strict (aucun cluster requis)
make iac           # les trois d'un coup
```

| Local (`make up`) | GCP (`infra/terraform`) |
|---|---|
| conteneur `pgvector/pgvector:pg16` | AlloyDB (cluster + primaire, IP privée) |
| conteneur `redis:7-alpine` | Memorystore (Private Service Access) |
| `logs/runs/*.jsonl` | bucket GCS versionné + rétention |
| `python -m arp.mcp` | Cloud Run v2, direct VPC egress, SA dédié |
| `python -m arp.api` (console) | Cloud Run v2, ingress interne, invoker vide |
| console statique (nginx) | Cloud Run v2, bundle statique, sans secret ni VPC |

Le DSN AlloyDB transite par **Secret Manager**, jamais par une variable d'env en
clair. Le service Cloud Run n'est **pas** invocable anonymement : `invoker_members`
est vide par défaut, chaque appelant doit être nommé explicitement.

**Outils.** `tofu` (OpenTofu) est le défaut ; `export TF=terraform` pour utiliser
Terraform HashiCorp. La validation K8s passe par `kubeconform` en conteneur car
`kubectl --dry-run=client` exige un API server joignable.

**Non déployé.** Aucun bloc `backend` n'est défini et aucun `apply` n'est lancé :
l'IaC est un livrable de conception, validé syntaxiquement et schématiquement.

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
index des runs). Détail des tâches dans
`docs/superpowers/plans/2026-07-23-agentic-retail-platform.md` et
`docs/superpowers/plans/2026-07-23-web-console.md`.
