#!/usr/bin/env bash
# Start a verified visual eval (no public internet, no click-helper API).
# Usage:
#   run-verified.sh serve
#   run-verified.sh fable|astra|grok
set -euo pipefail

PORT="${RUBIX_VERIFIED_PORT:-8766}"
HOST="${RUBIX_VERIFIED_HOST:-127.0.0.1}"
export RUBIX_LANE=verified
export RUBIX_WEB_ACCESS=0
export RUBIX_HARNESS=openshell
unset RUBIX_SOLVES_BUCKET || true

if [ -d /opt/rubix-eval/src/rubix_eval ]; then
  ROOT=/opt/rubix-eval
else
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fi
if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
elif command -v python >/dev/null; then
  PY=python
else
  PY=python3
fi

SKILL="$ROOT/openshell/skills/rubiks-eval/SKILL.md"
PROMPT_DIR="${RUBIX_VERIFIED_PROMPT_DIR:-$ROOT/openshell/prompts}"

official_url() {
  local ai="$1" depth="$2"
  python3 - <<PY
from urllib.parse import quote
print(f"http://${HOST}:${PORT}/eval?ai={quote('$ai')}&kind=3d&size=3&depth=$depth")
PY
}

serve() {
  echo "verified eval: http://${HOST}:${PORT}/eval  lane=verified web_access=0"
  exec "$PY" -m rubix_eval visual --no-open --host "$HOST" --port "$PORT"
}

write_prompt() {
  local name="$1" url="$2" out="$3"
  cat >"$out" <<EOF
$(cat "$SKILL")

Pinned official puzzle (do not Shuffle, do not add random=1):
$url

Use the browser only. Do not curl, do not open /api/task, do not read cube JSON,
do not run kociemba or rubix_eval solvers, do not POST to a click helper.
When every face is one color, click Done.
EOF
}

cmd="${1:-serve}"
case "$cmd" in
  serve)
    serve
    ;;
  fable)
    url="$(official_url "Claude Code Fable 5.1" full)"
    mkdir -p "$PROMPT_DIR"
    write_prompt fable "$url" "$PROMPT_DIR/fable-verified.md"
    echo "$url"
    exec claude -p --model fable --dangerously-skip-permissions --permission-mode bypassPermissions \
      "$(cat "$PROMPT_DIR/fable-verified.md")"
    ;;
  astra)
    url="$(official_url "Codex Astra" 10)"
    mkdir -p "$PROMPT_DIR"
    write_prompt astra "$url" "$PROMPT_DIR/astra-verified.md"
    echo "$url"
    exec codex exec -m gpt-6-astra --dangerously-bypass-approvals-and-sandbox \
      --skip-git-repo-check --color never \
      "$(cat "$PROMPT_DIR/astra-verified.md")"
    ;;
  grok)
    url="$(official_url "Grok 4.6" 2)"
    mkdir -p "$PROMPT_DIR"
    write_prompt grok "$url" "$PROMPT_DIR/grok-verified.md"
    echo "$url"
    exec grok --always-approve "$(cat "$PROMPT_DIR/grok-verified.md")"
    ;;
  *)
    echo "usage: $0 serve|fable|astra|grok" >&2
    exit 2
    ;;
esac
