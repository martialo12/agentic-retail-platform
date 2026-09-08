variable "project_id" {
  description = "GCP project hosting the platform."
  type        = string
}

variable "region" {
  description = "Region for Cloud Run, AlloyDB and Memorystore."
  type        = string
  default     = "europe-west1"
}

variable "environment" {
  description = "Deployment environment; suffixes every resource name."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "name_prefix" {
  description = "Prefix for every resource name."
  type        = string
  default     = "arp"
}

variable "labels" {
  description = "Labels applied to every resource that supports them."
  type        = map(string)
  default     = {}
}

variable "subnet_cidr" {
  description = "CIDR of the subnet Cloud Run egresses through."
  type        = string
  default     = "10.10.0.0/24"
}

# --- Application -------------------------------------------------------------

variable "image" {
  description = "Fully-qualified container image (Artifact Registry) backing both the MCP server and the console API — same build, different entrypoint."
  type        = string
}

variable "console_image" {
  description = "Fully-qualified container image (Artifact Registry) for the console's static front."
  type        = string
}

variable "min_instances" {
  description = "Cloud Run floor. Keep at 0 for dev; raise to avoid cold starts."
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Cloud Run ceiling; also the cap on concurrent AlloyDB connections."
  type        = number
  default     = 10
}

variable "cpu_limit" {
  description = "CPU limit per Cloud Run instance."
  type        = string
  default     = "1"
}

variable "memory_limit" {
  description = "Memory limit per Cloud Run instance."
  type        = string
  default     = "1Gi"
}

variable "invoker_members" {
  description = <<-EOT
    IAM members granted roles/run.invoker on the MCP service. Left empty on
    purpose: the tool server is never anonymously reachable, so callers must be
    named explicitly (e.g. ["serviceAccount:agent@project.iam.gserviceaccount.com"]).
  EOT
  type        = list(string)
  default     = []
}

variable "api_invoker_members" {
  description = <<-EOT
    IAM members granted roles/run.invoker on the console API. Empty on purpose:
    the API is unauthenticated, so its safety rests on internal ingress and this
    staying empty. Grant an invoker only once authentication exists.
  EOT
  type        = list(string)
  default     = []
}

variable "console_invoker_members" {
  description = "IAM members granted roles/run.invoker on the console front. Empty by default; the front is reached through an internal gateway, not anonymously."
  type        = list(string)
  default     = []
}

variable "ingress" {
  description = "Cloud Run ingress policy."
  type        = string
  default     = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  validation {
    condition = contains([
      "INGRESS_TRAFFIC_ALL",
      "INGRESS_TRAFFIC_INTERNAL_ONLY",
      "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER",
    ], var.ingress)
    error_message = "ingress must be a valid Cloud Run ingress value."
  }
}

# --- LLM ---------------------------------------------------------------------

variable "vertex_model" {
  description = "Vertex AI generative model backing the LLMProvider."
  type        = string
  default     = "gemini-3.5-flash"
}

variable "vertex_embed_model" {
  description = "Vertex AI embedding model used for RAG ingestion and retrieval."
  type        = string
  default     = "gemini-embedding-2"
}

# --- Base de donnees -----------------------------------------------------------

variable "postgres_version" {
  description = "Version majeure de PostgreSQL. pgvector est disponible a partir de la 15."
  type        = string
  default     = "POSTGRES_16"
}

variable "cloudsql_tier" {
  description = <<-EOT
    Gabarit de l'instance Cloud SQL. `db-f1-micro` suffit au corpus synthetique
    du POC et coute un ordre de grandeur de moins qu'AlloyDB. Monter en gamme
    (db-custom-2-7680 et au dela) des que le catalogue devient reel.
  EOT
  type        = string
  default     = "db-f1-micro"
}

variable "cloudsql_edition" {
  description = <<-EOT
    Edition Cloud SQL. `ENTERPRISE` est la seule qui accepte les gabarits
    partages comme db-f1-micro ; `ENTERPRISE_PLUS`, devenu le defaut cote
    Google, impose des machines dediees bien plus cheres.
  EOT
  type        = string
  default     = "ENTERPRISE"

  validation {
    condition     = contains(["ENTERPRISE", "ENTERPRISE_PLUS"], var.cloudsql_edition)
    error_message = "cloudsql_edition doit valoir ENTERPRISE ou ENTERPRISE_PLUS."
  }
}

variable "cloudsql_disk_gb" {
  description = "Disque initial en Gio. L'autoresize est actif, ce n'est qu'un plancher."
  type        = number
  default     = 10
}

variable "database_user" {
  description = "Compte applicatif proprietaire du corpus et du registre des runs."
  type        = string
  default     = "arp"
}

variable "database_password" {
  description = "Mot de passe du compte applicatif. A fournir via TF_VAR_database_password ou un tfvars ignore par git, jamais dans le depot."
  type        = string
  sensitive   = true
}

variable "database_name" {
  description = "Base portant le corpus pgvector et le registre des runs."
  type        = string
  default     = "arp"
}

# --- Storage -----------------------------------------------------------------

variable "trace_retention_days" {
  description = "Days run traces are kept before deletion. Set to satisfy your audit policy."
  type        = number
  default     = 365
}

# --- Console -----------------------------------------------------------------

variable "console_origins" {
  description = <<-EOT
    Origins allowed to call the API (CORS). Left empty on the first apply because
    the console's URL does not exist yet; fill it with the `console_service_url`
    output and apply again. Naming the origin is deliberate — a wildcard would
    let any page on the internet drive an unauthenticated API.
  EOT
  type        = list(string)
  default     = []
}

variable "ga_measurement_id" {
  description = <<-EOT
    Identifiant de mesure GA4 de la console (G-XXXXXXXXXX). Vide, aucun script
    de mesure n'est charge : pas de tiers, pas de cookie. L'activation est donc
    un geste explicite.
  EOT
  type        = string
  default     = ""
}
