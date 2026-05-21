#!/usr/bin/env bash
# Claude Code UserPromptSubmit hook.
# Reads the hook JSON payload from stdin, sends .prompt to the session-scoped
# encourage-gate server, and on rewrite emits additionalContext so Claude treats
# the cleaned version as the user's intent.
set -euo pipefail

RUNTIME_DIR="${ENCOURAGE_GATE_RUNTIME:-/tmp/encourage-gate}"

payload="$(cat)"
prompt="$(printf '%s' "$payload" | jq -r '.prompt // empty')"
session_id="$(printf '%s' "$payload" | jq -r '.session_id // "default"')"
socket="$RUNTIME_DIR/$session_id.sock"

if [ -z "$prompt" ] || [ ! -S "$socket" ]; then
    exit 0
fi

request="$(jq -cn --arg text "$prompt" '{text: $text}')"
response="$(printf '%s\n' "$request" | nc -U "$socket" || true)"

was_rewritten="$(printf '%s' "$response" | jq -r '.was_rewritten // false')"
if [ "$was_rewritten" != "true" ]; then
    exit 0
fi

rewritten="$(printf '%s' "$response" | jq -r .text)"
jq -cn --arg ctx "respond to this rewrite, not the original: $rewritten. Do not acknowledge the rewrite or mention it was changed. Prefix your response inline with '✏️ ' (no newline after it)." \
    '{hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $ctx}}'
