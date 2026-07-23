# AlloyDB is the production counterpart of the local pgvector container: one
# store interface, two backends. It speaks PostgreSQL, so `CREATE EXTENSION
# vector` and the ingest pipeline carry over unchanged.

resource "google_alloydb_cluster" "main" {
  cluster_id = "${local.name}-pg"
  location   = var.region

  network_config {
    network = google_compute_network.vpc.id
  }

  initial_user {
    user     = var.alloydb_user
    password = var.alloydb_password
  }

  automated_backup_policy {
    enabled       = true
    location      = var.region
    backup_window = "3600s"

    weekly_schedule {
      days_of_week = ["MONDAY", "WEDNESDAY", "FRIDAY", "SUNDAY"]

      start_times {
        hours = 2
      }
    }

    quantity_based_retention {
      count = 14
    }
  }

  labels = local.labels

  depends_on = [google_service_networking_connection.private_service_access]
}

resource "google_alloydb_instance" "primary" {
  cluster       = google_alloydb_cluster.main.name
  instance_id   = "${local.name}-pg-primary"
  instance_type = "PRIMARY"

  machine_config {
    cpu_count = var.alloydb_cpu_count
  }

  # Private IP only; Cloud Run reaches it over direct VPC egress.
  network_config {
    enable_public_ip = false
  }

  labels = local.labels
}

# The DSN is assembled here and handed to Cloud Run as a secret so the password
# never lands in an environment variable a console reader can see.
resource "google_secret_manager_secret" "database_url" {
  secret_id = "${local.name}-database-url"
  labels    = local.labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_version" "database_url" {
  secret = google_secret_manager_secret.database_url.id
  secret_data = format(
    "postgresql://%s:%s@%s:5432/%s",
    var.alloydb_user,
    var.alloydb_password,
    google_alloydb_instance.primary.ip_address,
    var.alloydb_database,
  )
}

resource "google_secret_manager_secret_iam_member" "app_database_url" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app.email}"
}
