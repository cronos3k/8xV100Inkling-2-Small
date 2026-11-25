#!/bin/bash
# oracle-serve.sh start [ctx] | stop | status
# The llama.cpp reference server for Inkling-2-Small (Unsloth UD-IQ2_XXS) on the eight cards, 127.0.0.1:18141.
# It is the oracle the engine port is compared against. Refuses to start while V4.1-Flash or another job holds the cards.
set -uo pipefail
source "$(dirname "$0")/ink2-env.sh"
P=$I/logs/oracle.pid; L=$I/logs/oracle.log; PORT=18141
M=$I/models/gguf/unsloth-small/UD-IQ2_XXS/Inkling-2-Small-UD-IQ2_XXS-00001-of-00005.gguf
export LD_LIBRARY_PATH=$V/rtlibs:$V/cuda-12.8/lib64 CUDA_DEVICE_ORDER=PCI_BUS_ID
alive() { [ -e "$P" ] && kill -0 "$(cat "$P")" 2> /dev/null; }
case "${1:-status}" in
  start)
    alive && { echo "already running, pid $(cat "$P")"; exit 0; }
    "$I/bin/v41-guard.sh" || exit 1
    ctx=${2:-32768}
    [ -e "$L" ] && mv "$L" "$L.prev"
    setsid nohup "$I/llama-build/bin/llama-server" -m "$M" -ngl 999 -c "$ctx" --parallel 1 \
      --host 127.0.0.1 --port $PORT --jinja --alias inkling-2-small-iq2 ${ORACLE_EXTRA:-} > "$L" 2>&1 < /dev/null &
    echo $! > "$P"; echo "started pid $(cat "$P"), ctx $ctx, log $L" ;;
  stop)
    if alive; then kill -TERM "$(cat "$P")"; echo "stop sent to $(cat "$P")"; else echo "not running"; fi ;;
  status)
    if alive; then echo "running, pid $(cat "$P")"; else echo "not running"; fi
    curl -s -m 3 "http://127.0.0.1:$PORT/health"; echo ;;
  *) echo "usage: $0 start [ctx] | stop | status"; exit 2 ;;
esac
