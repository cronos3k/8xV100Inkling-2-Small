#!/bin/bash
# small-b2-start.sh [DRAFTS]  Inkling-2-Small in the layout of the V4.1 reference setup: two NVLink boards, layers
# split once between them (25 + 23), four-way slicing inside each board, DSpark drafter on the second board.
# DRAFTS=0 starts without the drafter.
I=/srv/archive-a/volta-ink2
export INK2_CTX=${INK2_CTX:-8192} INK2_CHUNK=${INK2_CHUNK:-1024} INK2_GPUS=0,1,2,3,4,5,6,7 INK2_PARTITION=${INK2_PARTITION:-25,23}
export INK2_COMPILE=${INK2_COMPILE:-"{\"mode\":0,\"cudagraph_mode\":\"FULL_DECODE_ONLY\",\"cudagraph_capture_sizes\":[1,2,4,8]}"}
extra="--tensor-parallel-size 4 --pipeline-parallel-size 2 --max-num-seqs ${INK2_SEQS:-1}"
d=${1:-7}
if [ "$d" != 0 ]; then
  export VLLM_USE_V2_MODEL_RUNNER=1
  extra="$extra --speculative-config {\"method\":\"dspark\",\"num_speculative_tokens\":$d}"
fi
export ENGINE_EXTRA="--gpu-memory-utilization ${INK2_UTIL:-0.92} $extra ${INK2_EXTRA:-}"
exec $I/bin/engine-serve.sh start smallpp
