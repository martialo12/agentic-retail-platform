output "mcp_service_url" {
  description = "HTTPS endpoint of the MCP tool server."
  value       = google_cloud_run_v2_service.mcp.uri
}

output "api_service_url" {
  description = "HTTPS endpoint of the console API. Internal ingress; unauthenticated by design."
  value       = google_cloud_run_v2_service.api.uri
}

output "console_service_url" {
  description = "HTTPS endpoint of the console front."
  value       = google_cloud_run_v2_service.console.uri
}

output "service_account_email" {
  description = "Runtime identity of the Cloud Run service."
  value       = google_service_account.app.email
}

output "database_private_ip" {
  description = "Private IP of the AlloyDB primary."
  value       = google_sql_database_instance.main.private_ip_address
}

output "database_url_secret" {
  description = "Secret Manager secret holding the AlloyDB DSN."
  value       = google_secret_manager_secret.database_url.secret_id
}

output "traces_bucket" {
  description = "Bucket receiving the JSONL run traces."
  value       = google_storage_bucket.traces.name
}

output "corpus_bucket" {
  description = "Bucket holding the synthetic corpus staged for ingestion."
  value       = google_storage_bucket.corpus.name
}

output "vpc_network" {
  description = "Self link of the VPC the private services peer into."
  value       = google_compute_network.vpc.self_link
}

output "ingest_job" {
  description = "Cloud Run job embedding the corpus into AlloyDB. Run it after the first apply."
  value       = google_cloud_run_v2_job.ingest.name
}
