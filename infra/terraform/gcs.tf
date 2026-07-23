# Durable home for the JSONL run traces the tracer writes locally to logs/runs.
# Every run is auditable, which is what makes the platform AI-Act ready.

resource "google_storage_bucket" "traces" {
  name     = "${var.project_id}-${local.name}-traces"
  location = var.region

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = var.trace_retention_days
    }
    action {
      type = "Delete"
    }
  }

  labels = local.labels

  depends_on = [google_project_service.required]
}

resource "google_storage_bucket_iam_member" "app_traces_writer" {
  bucket = google_storage_bucket.traces.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.app.email}"
}

# Synthetic corpus staged for ingestion. Kept separate from traces so retention
# and access policies can diverge.
resource "google_storage_bucket" "corpus" {
  name     = "${var.project_id}-${local.name}-corpus"
  location = var.region

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  labels = local.labels

  depends_on = [google_project_service.required]
}

resource "google_storage_bucket_iam_member" "app_corpus_reader" {
  bucket = google_storage_bucket.corpus.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.app.email}"
}
