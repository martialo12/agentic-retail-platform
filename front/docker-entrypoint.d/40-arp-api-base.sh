#!/bin/sh
# Renders the console's runtime configuration before nginx starts.
#
# The API's URL only exists once the platform is deployed, so it cannot be baked
# into the bundle: the image would have to be rebuilt after every apply. nginx's
# own entrypoint runs everything in /docker-entrypoint.d, so this lands before
# the first request.
set -eu

target=/usr/share/nginx/html/config.js

if [ -z "${API_BASE:-}" ]; then
  echo "40-arp-api-base: API_BASE unset, keeping the build-time fallback"
  exit 0
fi

# Single quotes in a URL would break out of the string literal below.
case $API_BASE in
  *"'"*)
    echo "40-arp-api-base: refusing an API_BASE containing a quote" >&2
    exit 1
    ;;
esac

printf "window.__ARP_API_BASE__ = '%s'\n" "$API_BASE" > "$target"
echo "40-arp-api-base: API base set to $API_BASE"
