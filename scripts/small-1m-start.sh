#!/bin/bash
# small-1m-start.sh  Inkling-2-Small, sliced 8 ways, NVLink route, drafter, context 1,048,576 tokens.
# Memory is tight: exact cache size, prompt chunk 128, graphs for 1 and 8 tokens only.
I=/srv/archive-a/volta-ink2
export INK2_CTX=1048576
export INK2_COMPILE='{"mode":0,"cudagraph_mode":"FULL_DECODE_ONLY","cudagraph_capture_sizes":[1,8]}'
export INK2_EXTRA="--max-num-batched-tokens ${INK2_CHUNK:-128} --kv-cache-memory-bytes ${INK2_KV:-5637144576} --enable-prefix-caching"
exec $I/bin/small-draft-start.sh 7
