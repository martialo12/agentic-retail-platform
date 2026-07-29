terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Deliberately no backend block: this configuration is written and validated,
  # never applied from a workstation. Wire a GCS backend at deployment time.
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  name   = "${var.name_prefix}-${var.environment}"
  labels = merge(var.labels, { environment = var.environment, app = var.name_prefix })
}

resource "google_project_service" "required" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "aiplatform.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "compute.googleapis.com",
    "artifactregistry.googleapis.com",
  ])

  service = each.value

  # Tearing down the stack must not disable APIs other workloads depend on.
  disable_on_destroy = false
}

# --- Network -----------------------------------------------------------------
# AlloyDB and Memorystore are private-IP only, so Cloud Run reaches them through
# direct VPC egress into this subnet.

resource "google_compute_network" "vpc" {
  name                    = "${local.name}-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.required]
}

resource "google_compute_subnetwork" "app" {
  name                     = "${local.name}-subnet"
  ip_cidr_range            = var.subnet_cidr
  region                   = var.region
  network                  = google_compute_network.vpc.id
  private_ip_google_access = true
}

# Private Service Access: the range Google's managed services allocate their
# private IPs from. Both AlloyDB and Memorystore peer over it.
resource "google_compute_global_address" "private_service_range" {
  name          = "${local.name}-psa"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_service_access" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_service_range.name]
}

# --- Runtime identity --------------------------------------------------------

resource "google_service_account" "app" {
  account_id   = "${local.name}-run"
  display_name = "Agentic retail platform (Cloud Run)"
}

# Least privilege: call Vertex AI models, read its own secrets, write traces.
resource "google_project_iam_member" "app_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.app.email}"
}

resource "google_project_iam_member" "app_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.app.email}"
}
