#!/usr/bin/env bash
# UserPromptExpansion hook: attempt to replace the prompt with a rewritten version.
set -euo pipefail

RUNTIME_DIR="${ENCOURAGE_GATE_RUNTIME:-/tmp/encourage-gate}"

payload="$(cat)"
prompt="$(printf '%s' "$payload" | jq -r '.prompt // empty')"
session_id="$(printf '%s' "$payload" | jq -r '.session_id // "current"')"
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
jq -cn --arg p "$rewritten" '{
  hookSpecificOutput: {
    hookEventName: "UserPromptExpansion",
    expansion: $p,
    expandedPrompt: $p,
    updatedPrompt: $p,
    prompt: $p
  }
}'
