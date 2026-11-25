#!/bin/bash
# download2.sh: segmented continuation of download.sh (many range streams per file, both uplinks).
# Fetches what is still missing of the 2-bit Small GGUF and of Mini, then verifies every file by sha256.
# Start detached. Progress: $I/logs/download.log   Finished: $I/logs/download.done holds 0 (all verified) or 1.
set -uo pipefail
source "$(dirname "$0")/ink2-env.sh"
L=$I/logs/download.log; rc=0
export INK2_SEG_STREAMS="${INK2_SEG_STREAMS:-enp184s0f1:16 enp97s0f3np3:2}"
echo "$(date "+%F %T") download2.sh start, streams: $INK2_SEG_STREAMS" >> "$L"
seg() { python3 "$I/bin/fetch-seg.py" "$@" >> "$L" 2>&1 || rc=1; }
ver() { python3 "$I/bin/fetch.py" "$@" --verify-only >> "$L" 2>&1 || rc=1; }
seg unsloth/Inkling-2-Small-GGUF    "$I/models/gguf/unsloth-small" "UD-IQ2_XXS/*"
seg thinkingmachines/Inkling-2-Mini "$I/models/mini-nvfp4" "*"
ver unsloth/Inkling-2-Small-GGUF     "$I/models/gguf/unsloth-small" "UD-IQ2_XXS/*" "mmproj-F16.gguf" "imatrix_unsloth.gguf_file"
ver thinkingmachines/Inkling-2-Mini  "$I/models/mini-nvfp4" "*"
ver thinkingmachines/Inkling-2-Small "$I/models/base-small" "*.json" "*.jinja" "tiktoken/*" "README.md" "mtp.safetensors"
echo $rc > "$I/logs/download.done"
echo "$(date "+%F %T") download2.sh finished with $rc" >> "$L"
