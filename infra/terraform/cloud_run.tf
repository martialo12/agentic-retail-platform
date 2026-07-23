resource "google_cloud_run_v2_service" "mcp" {
  name     = "${local.name}-mcp"
  location = var.region
  ingress  = var.ingress

  # This is a POC stack; let `destroy` actually destroy.
  deletion_protection = false

  labels = local.labels

  template {
    service_account = google_service_account.app.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    # Direct VPC egress (no connector VM) — private ranges only, so calls to
    # Vertex AI still leave over the internet path.
    vpc_access {
      egress = "PRIVATE_RANGES_ONLY"

      network_interfaces {
        network    = google_compute_network.vpc.id
        subnetwork = google_compute_subnetwork.app.id
      }
    }

    containers {
      image = var.image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
      }

      env {
        name  = "LLM_PROVIDER"
        value = "vertex"
      }

      env {
        name  = "VERTEX_PROJECT"
        value = var.project_id
      }

      env {
        name  = "VERTEX_LOCATION"
        value = var.region
      }

      env {
        name  = "VERTEX_MODEL"
        value = var.vertex_model
      }

      env {
        name  = "VERTEX_EMBED_MODEL"
        value = var.vertex_embed_model
      }

      env {
        name  = "REDIS_URL"
        value = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/0"
      }

      env {
        name  = "TRACE_BUCKET"
        value = google_storage_bucket.traces.name
      }

      env {
        name = "DATABASE_URL"

        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        tcp_socket {
          port = 8080
        }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 6
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_secret_manager_secret_iam_member.app_database_url,
    google_alloydb_instance.primary,
  ]
}

# The MCP server is the door to business logic; it is never anonymously callable.
# Callers authenticate with an ID token and need this role explicitly.
resource "google_cloud_run_v2_service_iam_member" "invokers" {
  for_each = toset(var.invoker_members)

  name     = google_cloud_run_v2_service.mcp.name
  location = google_cloud_run_v2_service.mcp.location
  role     = "roles/run.invoker"
  member   = each.value
}

# --- Console API -------------------------------------------------------------
# The same image as the MCP server, a different entrypoint. The API is
# unauthenticated by design (FR-018), so the safety here is structural, not a
# README warning: internal ingress plus an empty invoker set. The configuration
# cannot accidentally publish it; granting an invoker is a deliberate act that
# must wait until authentication exists.
resource "google_cloud_run_v2_service" "api" {
  name     = "${local.name}-api"
  location = var.region
  ingress  = var.ingress

  deletion_protection = false

  labels = local.labels

  template {
    service_account = google_service_account.app.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    vpc_access {
      egress = "PRIVATE_RANGES_ONLY"

      network_interfaces {
        network    = google_compute_network.vpc.id
        subnetwork = google_compute_subnetwork.app.id
      }
    }

    containers {
      image = var.image

      # Override the image's default CMD (python -m arp.mcp).
      args = ["python", "-m", "arp.api"]

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
      }

      # The API binds API_PORT; the container port above must match it.
      env {
        name  = "API_PORT"
        value = "8080"
      }

      env {
        name  = "LLM_PROVIDER"
        value = "vertex"
      }

      env {
        name  = "VERTEX_PROJECT"
        value = var.project_id
      }

      env {
        name  = "VERTEX_LOCATION"
        value = var.region
      }

      env {
        name  = "VERTEX_MODEL"
        value = var.vertex_model
      }

      env {
        name  = "VERTEX_EMBED_MODEL"
        value = var.vertex_embed_model
      }

      env {
        name  = "REDIS_URL"
        value = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/0"
      }

      env {
        name  = "TRACE_BUCKET"
        value = google_storage_bucket.traces.name
      }

      env {
        name = "DATABASE_URL"

        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        tcp_socket {
          port = 8080
        }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 6
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_secret_manager_secret_iam_member.app_database_url,
    google_alloydb_instance.primary,
  ]
}

# Its own invoker set, kept separate from the MCP server's so granting one never
# grants the other. Empty until authentication lands — see the note above.
resource "google_cloud_run_v2_service_iam_member" "api_invokers" {
  for_each = toset(var.api_invoker_members)

  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = each.value
}

# --- Console front -----------------------------------------------------------
# The static bundle behind nginx. It touches nothing — no database, no Redis, no
# Vertex — so it runs under an identity with no role bindings at all, and needs
# neither VPC egress nor secrets.
resource "google_service_account" "console" {
  account_id   = "${local.name}-console"
  display_name = "Agentic retail console (static front)"
}

resource "google_cloud_run_v2_service" "console" {
  name     = "${local.name}-console"
  location = var.region
  ingress  = var.ingress

  deletion_protection = false

  labels = local.labels

  template {
    service_account = google_service_account.console.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.console_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
      }

      startup_probe {
        tcp_socket {
          port = 8080
        }
        initial_delay_seconds = 3
        period_seconds        = 5
        failure_threshold     = 6
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_v2_service_iam_member" "console_invokers" {
  for_each = toset(var.console_invoker_members)

  name     = google_cloud_run_v2_service.console.name
  location = google_cloud_run_v2_service.console.location
  role     = "roles/run.invoker"
  member   = each.value
}
