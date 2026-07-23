# Memorystore replaces the local redis container: retrieval and tool-result
# caching. Private Service Access keeps it off the public internet.

resource "google_redis_instance" "cache" {
  name           = "${local.name}-cache"
  tier           = var.redis_tier
  memory_size_gb = var.redis_memory_gb
  region         = var.region

  authorized_network = google_compute_network.vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  redis_version           = "REDIS_7_2"
  transit_encryption_mode = "SERVER_AUTHENTICATION"

  labels = local.labels

  depends_on = [google_service_networking_connection.private_service_access]
}
