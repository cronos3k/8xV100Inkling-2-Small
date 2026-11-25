#!/bin/bash
# Stop the Inkling web interface and its speech service. The model server keeps running.
source "$(dirname "$0")/ink-common.sh"
for s in caddy opencode speech; do
  if svc_ok $s; then
    P=$(cat "$STATE/$s.pid"); kill -TERM -- "-$P" 2>/dev/null || kill -TERM "$P" 2>/dev/null
    echo "$s: stop sent to $P"
  else
    echo "$s: not running"
  fi
done
