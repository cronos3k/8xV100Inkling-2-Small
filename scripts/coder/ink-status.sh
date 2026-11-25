#!/bin/bash
source "$(dirname "$0")/ink-common.sh"
if llm_proc_ok; then echo "Inkling process: running, pid $(llm_pid)"; else echo "Inkling process: not running"; fi
if llm_answers; then echo "Inkling api:     answering on http://127.0.0.1:$(llm_port)/v1 (model $MODEL)"; else echo "Inkling api:     not answering on port $(llm_port)"; fi
if v41_answers; then echo "DeepSeek-V4.1-Flash: running (it holds the cards)"; else echo "DeepSeek-V4.1-Flash: not running"; fi
for s in speech opencode caddy; do
  if svc_ok $s; then echo "web $s: running, port $(cat "$STATE/$s.port" 2>/dev/null)"; else echo "web $s: not running"; fi
done
if svc_ok caddy; then for ip in $(lan_ips); do echo "  https://$ip:$(cat "$STATE/caddy.port")"; done; fi
nvidia-smi --query-gpu=index,memory.used,utilization.gpu,power.draw --format=csv,noheader 2>/dev/null
