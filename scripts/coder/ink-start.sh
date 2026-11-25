#!/bin/bash
# Start Inkling-2-Small (8 cards, drafter, context 1,048,576). Only one model fits on the cards:
# if DeepSeek-V4.1-Flash is running, stop it first with ~/coder/stop.sh.
#   ink-start.sh          1M context profile
#   ink-start.sh short    8K context, larger prompt chunk (quick tests)
source "$(dirname "$0")/ink-common.sh"
if llm_answers; then echo "already running: pid $(llm_pid), http://127.0.0.1:$(llm_port)/v1"; exit 0; fi
if v41_answers; then echo "DeepSeek-V4.1-Flash is running and holds the cards. Stop it first: ~/coder/stop.sh"; exit 1; fi
if ! llm_proc_ok; then
  if [ "${1:-}" = short ]; then "$I/bin/small-draft-start.sh" 7; else "$I/bin/small-1m-start.sh"; fi > "$INK/logs/start.log" 2>&1
  tail -1 "$INK/logs/start.log"
  sleep 3
  llm_proc_ok || { echo "start failed; see $INK/logs/start.log and $I/logs/engine.log"; exit 1; }
fi
for i in $(seq 1 180); do
  llm_answers && { echo "ready after about $((i*5)) s: http://127.0.0.1:$(llm_port)/v1"; exit 0; }
  llm_proc_ok || { echo "the server exited during load; see $I/logs/engine.log"; grep -E "Error|out of memory" "$I/logs/engine.log" | tail -3; exit 1; }
  sleep 5; printf .
done
echo; echo "not ready after 15 minutes; see $I/logs/engine.log"; exit 1
