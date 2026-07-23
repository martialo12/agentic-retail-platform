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
  description = "Fully-qualified container image (Artifact Registry) for the MCP server."
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

# --- AlloyDB -----------------------------------------------------------------

variable "alloydb_cpu_count" {
  description = "vCPUs on the AlloyDB primary instance."
  type        = number
  default     = 2
}

variable "alloydb_user" {
  description = "Initial AlloyDB superuser."
  type        = string
  default     = "arp"
}

variable "alloydb_password" {
  description = "Initial AlloyDB password. Supply via TF_VAR_alloydb_password, never in VCS."
  type        = string
  sensitive   = true
}

variable "alloydb_database" {
  description = "Database holding the pgvector corpus."
  type        = string
  default     = "arp"
}

# --- Memorystore -------------------------------------------------------------

variable "redis_tier" {
  description = "Memorystore tier. STANDARD_HA gives a replica and automatic failover."
  type        = string
  default     = "BASIC"

  validation {
    condition     = contains(["BASIC", "STANDARD_HA"], var.redis_tier)
    error_message = "redis_tier must be BASIC or STANDARD_HA."
  }
}

variable "redis_memory_gb" {
  description = "Memorystore capacity in GiB."
  type        = number
  default     = 1
}

# --- Storage -----------------------------------------------------------------

variable "trace_retention_days" {
  description = "Days run traces are kept before deletion. Set to satisfy your audit policy."
  type        = number
  default     = 365
}
