#!/bin/bash
# v41-guard.sh: exit 0 when the eight cards are free for Inkling work, 1 otherwise.
# It never stops anything. A running V4.1-Flash server always wins.
if pgrep -f "vllm.entrypoints.openai.api_server.*run-pp2" > /dev/null; then
  echo "V4.1-Flash server is running; Inkling work does not start"; exit 1
fi
busy=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 > 500 {n++} END {print n + 0}')
if [ "$busy" != 0 ]; then
  echo "$busy card(s) hold memory of another job; Inkling work does not start"
  nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv,noheader
  exit 1
fi
echo "cards free"
