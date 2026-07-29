// Rewritten by the container at start-up from the API_BASE environment
// variable (see docker-entrypoint.d/40-arp-api-base.sh). Left empty here so a
// source checkout falls back to VITE_API_BASE, then to localhost.
window.__ARP_API_BASE__ = ''
