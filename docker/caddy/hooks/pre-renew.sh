#!/bin/sh
set -eu

STATE_FILE="/tmp/novotech_ingress_was_running"

rm -f "$STATE_FILE"

if docker ps --format '{{.Names}}' | grep -qx 'novotech_ingress'; then
  touch "$STATE_FILE"
  docker stop novotech_ingress >/dev/null
fi

for _ in $(seq 1 15); do
  if ! ss -ltn '( sport = :80 or sport = :443 )' | grep -q LISTEN; then
    exit 0
  fi
  sleep 1
done

echo "ports 80/443 are still busy before certificate renewal" >&2
exit 1
