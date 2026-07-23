output "mcp_service_url" {
  description = "HTTPS endpoint of the MCP tool server."
  value       = google_cloud_run_v2_service.mcp.uri
}

output "service_account_email" {
  description = "Runtime identity of the Cloud Run service."
  value       = google_service_account.app.email
}

output "alloydb_instance_ip" {
  description = "Private IP of the AlloyDB primary."
  value       = google_alloydb_instance.primary.ip_address
}

output "database_url_secret" {
  description = "Secret Manager secret holding the AlloyDB DSN."
  value       = google_secret_manager_secret.database_url.secret_id
}

output "redis_host" {
  description = "Private host of the Memorystore instance."
  value       = google_redis_instance.cache.host
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
