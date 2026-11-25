#!/bin/bash
# Stop the Inkling model server (only the process group in its own pid file).
source "$(dirname "$0")/ink-common.sh"
llm_proc_ok || { echo "not running"; exit 0; }
P=$(llm_pid)
echo "stopping pid/pgid $P"
kill -TERM -- "-$P" 2>/dev/null || kill -TERM "$P"
for i in $(seq 1 60); do kill -0 "$P" 2>/dev/null || { echo "stopped"; exit 0; }; sleep 1; done
echo "still running after 60 s; forcing"; kill -KILL -- "-$P" 2>/dev/null; sleep 2
kill -0 "$P" 2>/dev/null && { echo "could not stop $P"; exit 1; }
echo "stopped"
