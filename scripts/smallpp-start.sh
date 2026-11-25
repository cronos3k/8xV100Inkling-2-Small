#!/bin/bash
# smallpp-start.sh   Start Inkling-2-Small split by layer (one run of whole layers per card) with CUDA graphs.
# Environment: INK2_CTX (context, default 8192), INK2_CHUNK (prompt chunk, default 512), INK2_SEQS (default 4).
I=/srv/archive-a/volta-ink2
export INK2_CTX=${INK2_CTX:-8192} INK2_CHUNK=${INK2_CHUNK:-512}
export INK2_COMPILE=${INK2_COMPILE:-"{\"mode\":0,\"cudagraph_mode\":\"FULL_DECODE_ONLY\",\"cudagraph_capture_sizes\":[1,2,4]}"}
export ENGINE_EXTRA="--gpu-memory-utilization ${INK2_UTIL:-0.95} ${INK2_EXTRA:-}"
exec $I/bin/engine-serve.sh start smallpp
