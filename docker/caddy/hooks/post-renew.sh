#!/bin/sh
set -eu

STATE_FILE="/tmp/novotech_ingress_was_running"

if [ -f "$STATE_FILE" ]; then
  rm -f "$STATE_FILE"
  cd /root/project_shop/novotech
  docker compose up -d ingress autoheal >/dev/null
fi
