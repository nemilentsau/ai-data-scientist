#!/usr/bin/env bash
# Hook script that appends every tool-use event to a JSONL trace file.
# TRACE_FILE must be set as an environment variable before the session starts.
# Called by PostToolUse, PostToolUseFailure, SessionStart, and SessionEnd hooks.
set -euo pipefail

INPUT=$(cat)

# Fall back to a default if TRACE_FILE isn't set (shouldn't happen in benchmark)
TRACE_FILE="${TRACE_FILE:-/tmp/claude-trace.jsonl}"

echo "$INPUT" | jq -c '{
  timestamp: (now | todate),
  session_id: .session_id,
  event: .hook_event_name,
  tool: (.tool_name // null),
  tool_input: (.tool_input // null),
  tool_response: (
    if .tool_response then
      (.tool_response | tostring | if length > 2000 then .[0:2000] + "…[truncated]" else . end)
    else null end
  ),
  error: (.error // null),
  cwd: .cwd
}' >> "$TRACE_FILE"

exit 0
