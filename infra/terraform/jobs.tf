# Corpus ingestion, as an on-demand Cloud Run job.
#
# The store creates its own `vector` extension and table on first write
# (src/arp/rag/store.py), so AlloyDB needs no schema bootstrap — but it does
# need the corpus embedded into it, or every retrieval comes back empty and the
# agents answer from nothing. That is a one-shot task, not a server, so it runs
# as a job: same image, same identity, same secret, `python -m arp.rag.ingest`
# instead of the default entrypoint.
#
# Run it after the first apply, and again whenever the corpus or the embedding
# model changes:
#   gcloud run jobs execute arp-dev-ingest --region europe-west1 --wait

resource "google_cloud_run_v2_job" "ingest" {
  name     = "${local.name}-ingest"
  location = var.region

  deletion_protection = false

  labels = local.labels

  template {
    template {
      service_account = google_service_account.app.email

      # One retry: the failure worth retrying is a cold AlloyDB connection, and
      # ingestion is idempotent. Beyond that, a rerun should be a decision.
      max_retries = 1

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
        args = ["python", "-m", "arp.rag.ingest"]

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
          name  = "VERTEX_EMBED_MODEL"
          value = var.vertex_embed_model
        }

        env {
          name  = "LOG_FORMAT"
          value = "json"
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
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.app_database_url,
    # La version, pas seulement le conteneur du secret : Cloud Run resout
    # `versions/latest` a la creation et echoue si aucune version n'existe
    # encore. L'instance seule ne suffit pas, la version attend aussi la base
    # et l'utilisateur.
    google_secret_manager_secret_version.database_url,
    google_sql_database_instance.main,
  ]
}
