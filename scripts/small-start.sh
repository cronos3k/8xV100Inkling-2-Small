#!/bin/bash
# small-start.sh [topo]   Start Inkling-2-Small on the engine with the current best settings.
#   topo = also let the engine measure its own NVLink-routed all-reduce against NCCL and use the winner.
I=/srv/archive-a/volta-ink2
export INK2_CTX=${INK2_CTX:-8192}
export INK2_COMPILE='{"mode":0,"cudagraph_mode":"FULL_DECODE_ONLY","cudagraph_capture_sizes":[1,2,4]}'
extra="--gpu-memory-utilization 0.95 --max-num-batched-tokens 512"
if [ "$1" = topo ]; then
  # 1 token: 9216 (layer output) and 36864 (expert activation); 2 and 4 parallel requests: the multiples
  export VLLM_INK2_AR_WIDTHS=${VLLM_INK2_AR_WIDTHS:-18432,36864,73728,147456}
  extra="$extra --kernel-config {\"topology_all_reduce\":{\"enabled\":true,\"cache_dir\":\"$I/cache/topology-selections\"}}"
fi
export ENGINE_EXTRA="$extra"
exec $I/bin/engine-serve.sh start small
