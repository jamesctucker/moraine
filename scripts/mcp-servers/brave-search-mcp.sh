#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="$(dirname "$0")/../../.opencode/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

exec bunx -y @brave/brave-search-mcp-server "$@"
