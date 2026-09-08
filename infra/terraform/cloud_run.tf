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

      # Cloud Logging n'indexe les champs que si la sortie est structuree.
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
    # La version, pas seulement le conteneur du secret : Cloud Run resout
    # `versions/latest` a la creation et echoue si aucune version n'existe
    # encore. L'instance seule ne suffit pas, la version attend aussi la base
    # et l'utilisateur.
    google_secret_manager_secret_version.database_url,
    google_sql_database_instance.main,
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

      # The console is a different origin, so it must be named. Deliberately a
      # variable rather than a reference to the console service: the console
      # already reads this service's URL, and referencing it back would cycle.
      # First apply leaves it empty, then set console_origins to the
      # `console_service_url` output and apply again.
      env {
        name  = "CORS_ORIGINS"
        value = join(",", var.console_origins)
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

      # Cloud Logging n'indexe les champs que si la sortie est structuree.
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
    # La version, pas seulement le conteneur du secret : Cloud Run resout
    # `versions/latest` a la creation et echoue si aucune version n'existe
    # encore. L'instance seule ne suffit pas, la version attend aussi la base
    # et l'utilisateur.
    google_secret_manager_secret_version.database_url,
    google_sql_database_instance.main,
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

      # Read at start-up by the image's entrypoint, which rewrites /config.js.
      # The bundle therefore never hardcodes an API URL, and the reference runs
      # one way only — console depends on api, never the reverse, or the graph
      # would cycle. The API learns the console's origin through
      # `var.console_origins` instead (see CORS_ORIGINS above).
      env {
        name  = "API_BASE"
        value = google_cloud_run_v2_service.api.uri
      }

      # Vide par defaut : la console ne mesure rien tant qu'un identifiant n'est
      # pas fourni explicitement.
      env {
        name  = "GA_MEASUREMENT_ID"
        value = var.ga_measurement_id
      }

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
