#!/usr/bin/env bash
# Wait for an HTTP endpoint or host:port to become reachable.
set -euo pipefail
target="${1:?usage: wait-for.sh URL_OR_HOST:PORT [timeout_s]}"
timeout="${2:-60}"
deadline=$((SECONDS + timeout))
while [ $SECONDS -lt $deadline ]; do
  if [[ "$target" == http* ]]; then
    if curl -sf "$target" >/dev/null 2>&1; then exit 0; fi
  else
    host="${target%:*}"
    port="${target##*:}"
    if (echo >"/dev/tcp/$host/$port") >/dev/null 2>&1; then exit 0; fi
  fi
  sleep 1
done
echo "timed out waiting for $target" >&2
exit 1
