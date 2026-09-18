#!/usr/bin/env bash
# OpenShell Docker sandboxes call the host at 172.18.0.1:17670 (bridge gateway).
# UFW on this machine drops that INPUT, so the supervisor never fetches policy
# and the container exits. Run once with sudo:
set -euo pipefail
PORT="${OPENSHELL_SERVER_PORT:-17670}"
if [ "$(id -u)" -ne 0 ]; then
  echo "usage: sudo $0" >&2
  exit 2
fi
if command -v ufw >/dev/null; then
  ufw allow proto tcp from 172.18.0.0/16 to any port "$PORT" comment 'openshell sandbox -> gateway'
  ufw status | grep "$PORT" || true
fi
iptables -C INPUT -s 172.18.0.0/16 -p tcp --dport "$PORT" -j ACCEPT 2>/dev/null \
  || iptables -I INPUT -s 172.18.0.0/16 -p tcp --dport "$PORT" -j ACCEPT
echo "allowed 172.18.0.0/16 -> tcp/$PORT"
