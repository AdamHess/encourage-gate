#!/usr/bin/env bash
# SessionEnd hook: stop the session's encourage-gate server and clean up.
set -euo pipefail

RUNTIME_DIR="${ENCOURAGE_GATE_RUNTIME:-/tmp/encourage-gate}"

payload="$(cat)"
session_id="$(printf '%s' "$payload" | jq -r '.session_id // "default"')"

socket="$RUNTIME_DIR/$session_id.sock"
pidfile="$RUNTIME_DIR/$session_id.pid"

if [ -f "$pidfile" ]; then
    pid="$(cat "$pidfile")"
    kill -TERM "$pid" 2>/dev/null || true
    rm -f "$pidfile"
fi
rm -f "$socket"
