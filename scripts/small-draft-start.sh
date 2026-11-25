#!/bin/bash
# small-draft-start.sh [DRAFTS]  Inkling-2-Small, sliced 8 ways, NVLink route, with the bundled DSpark drafter.
I=/srv/archive-a/volta-ink2
export INK2_CTX=${INK2_CTX:-8192} VLLM_USE_V2_MODEL_RUNNER=1
export VLLM_INK2_AR_WIDTHS=${VLLM_INK2_AR_WIDTHS:-18432,36864,73728,147456}
export INK2_COMPILE=${INK2_COMPILE:-"{\"mode\":0,\"cudagraph_mode\":\"FULL_DECODE_ONLY\",\"cudagraph_capture_sizes\":[1,2,4,8]}"}
export ENGINE_EXTRA="--gpu-memory-utilization ${INK2_UTIL:-0.95} --max-num-batched-tokens 512 --max-num-seqs 1 --speculative-config {\"method\":\"dspark\",\"num_speculative_tokens\":${1:-7}} ${INK2_EXTRA:-}"
exec $I/bin/engine-serve.sh start small
