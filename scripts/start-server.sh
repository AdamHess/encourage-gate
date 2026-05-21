#!/usr/bin/env bash
# SessionStart hook: launch the encourage-gate server in the background
# with a session-scoped socket. Reads session_id from the hook JSON on stdin.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="${ENCOURAGE_GATE_RUNTIME:-/tmp/encourage-gate}"
mkdir -p "$RUNTIME_DIR"

payload="$(cat)"
session_id="$(printf '%s' "$payload" | jq -r '.session_id // "default"')"

socket="$RUNTIME_DIR/$session_id.sock"
pidfile="$RUNTIME_DIR/$session_id.pid"
logfile="$RUNTIME_DIR/$session_id.log"

# If already running for this session, do nothing (handles SessionStart on resume).
if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    exit 0
fi

cd "$PROJECT_DIR"
ENCOURAGE_GATE_SOCKET_PATH="$socket" \
    nohup "$PROJECT_DIR/.venv/bin/encourage-gate-server" \
    > "$logfile" 2>&1 &
echo $! > "$pidfile"
