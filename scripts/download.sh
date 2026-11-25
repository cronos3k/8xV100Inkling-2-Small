#!/bin/bash
# download.sh: fetch everything stages 0-2 need into $I/models. Resumable; run it again after an interruption.
# Start detached:  setsid nohup $I/bin/download.sh > /dev/null 2>&1 &
# Progress: $I/logs/download.log   Finished: $I/logs/download.done holds 0 (all verified) or 1.
set -uo pipefail
source "$(dirname "$0")/ink2-env.sh"
L=$I/logs/download.log; mkdir -p "$I/logs" "$I/models"
[ -e "$I/logs/download.done" ] && mv "$I/logs/download.done" "$I/logs/download.done.prev"
rc=0
f() { python3 "$I/bin/fetch.py" "$@" >> "$L" 2>&1 || rc=1; }
# small first: configuration, tokenizer and chat template of both models
f thinkingmachines/Inkling-2-Small "$I/models/base-small" "*.json" "*.jinja" "tiktoken/*" "README.md"
f unsloth/Inkling-2-Small-GGUF     "$I/models/gguf/unsloth-small" "README.md" "mmproj-F16.gguf" "imatrix_unsloth.gguf_file"
# the 2-bit model, 190.6 GB in 5 shards
f unsloth/Inkling-2-Small-GGUF     "$I/models/gguf/unsloth-small" "UD-IQ2_XXS/*" --jobs 4
# Inkling-2-Mini in its native NVFP4 form, 20.2 GB, for the engine bring-up
f thinkingmachines/Inkling-2-Mini  "$I/models/mini-nvfp4" "*" --jobs 2
echo $rc > "$I/logs/download.done"
echo "$(date "+%F %T") download.sh finished with $rc" >> "$L"
