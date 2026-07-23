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
