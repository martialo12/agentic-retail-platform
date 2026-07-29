# Cloud SQL for PostgreSQL, contrepartie de production du conteneur pgvector
# local. Une interface de store, deux moteurs.
#
# Pourquoi pas AlloyDB : `src/arp/rag/store.py` ecrit du pgvector standard, sans
# extension proprietaire, et le registre des runs est un simple Postgres. Rien
# dans le code ne reclame AlloyDB, dont l'instance primaire minimale est de deux
# vCPU sans mise a l'echelle a zero. Cloud SQL sert le meme SQL pour un ordre de
# grandeur de moins, et peut etre arretee entre deux demonstrations.
#
# Le contrat vis-a-vis de l'application est inchange : IP privee joignable par
# Cloud Run en egress VPC direct, et un DSN livre par Secret Manager.

resource "google_sql_database_instance" "main" {
  name             = "${local.name}-pg"
  database_version = var.postgres_version
  region           = var.region

  # Un POC detruit et redeploye souvent : une suppression ne doit pas exiger un
  # detour par la console. A repasser a true pour un environnement durable.
  deletion_protection = false

  settings {
    tier = var.cloudsql_tier

    # Sans cette ligne, Google cree l'instance en edition Enterprise Plus, qui
    # refuse les gabarits partages : "Invalid Tier (db-f1-micro) for
    # (ENTERPRISE_PLUS) Edition". Enterprise est l'edition qui porte les petits
    # gabarits, et la seule qui ait du sens pour une demonstration.
    edition           = var.cloudsql_edition
    availability_type = "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = var.cloudsql_disk_gb
    disk_autoresize   = true

    ip_configuration {
      # Pas d'IP publique : la base n'est joignable que depuis le VPC.
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.vpc.id
      enable_private_path_for_google_cloud_services = true
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "02:00"
      point_in_time_recovery_enabled = false

      backup_retention_settings {
        retained_backups = 7
      }
    }

    user_labels = local.labels
  }

  depends_on = [google_service_networking_connection.private_service_access]
}

resource "google_sql_database" "main" {
  name     = var.database_name
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app" {
  name     = var.database_user
  instance = google_sql_database_instance.main.name
  password = var.database_password
}

# Le DSN est assemble ici et remis a Cloud Run comme secret, pour que le mot de
# passe n'atterrisse jamais dans une variable d'environnement lisible en console.
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
    var.database_user,
    var.database_password,
    google_sql_database_instance.main.private_ip_address,
    var.database_name,
  )

  depends_on = [google_sql_user.app, google_sql_database.main]
}

resource "google_secret_manager_secret_iam_member" "app_database_url" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app.email}"
}
