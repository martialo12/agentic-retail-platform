#!/bin/sh
# Renders the console's runtime configuration before nginx starts.
#
# The API's URL only exists once the platform is deployed, so it cannot be baked
# into the bundle: the image would have to be rebuilt after every apply. nginx's
# own entrypoint runs everything in /docker-entrypoint.d, so this lands before
# the first request.
set -eu

target=/usr/share/nginx/html/config.js

# Une apostrophe casserait le litteral javascript ecrit plus bas.
reject_quote() {
  case $1 in
    *"'"*)
      echo "40-arp-api-base: refusing a value containing a quote" >&2
      exit 1
      ;;
  esac
}

if [ -z "${API_BASE:-}" ] && [ -z "${GA_MEASUREMENT_ID:-}" ]; then
  echo "40-arp-api-base: API_BASE and GA_MEASUREMENT_ID unset, keeping build-time defaults"
  exit 0
fi

: > "$target"

if [ -n "${API_BASE:-}" ]; then
  reject_quote "$API_BASE"
  printf "window.__ARP_API_BASE__ = '%s'\n" "$API_BASE" >> "$target"
  echo "40-arp-api-base: API base set to $API_BASE"
fi

# Sans identifiant, aucun script de mesure n'est charge : pas de tiers, pas de
# cookie. L'activation est donc un geste explicite, par variable d'environnement.
if [ -n "${GA_MEASUREMENT_ID:-}" ]; then
  reject_quote "$GA_MEASUREMENT_ID"
  printf "window.__ARP_GA_ID__ = '%s'\n" "$GA_MEASUREMENT_ID" >> "$target"
  echo "40-arp-api-base: analytics enabled ($GA_MEASUREMENT_ID)"
fi
