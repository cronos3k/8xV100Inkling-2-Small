#!/bin/bash
# build-llama.sh: llama.cpp master for SM70 inside $I, as the reference ("oracle") for Inkling-2-Small.
# Uses the CUDA 12.8 toolkit of the V4.1 tree by path only; nothing is written there.
# Start detached; log $I/logs/build-llama.log; result in $I/logs/build-llama.done (OK or FAIL ...).
set -uo pipefail
source "$(dirname "$0")/ink2-env.sh"
C=$V/cuda-12.8; S=$I/llama.cpp; B=$I/llama-build; L=$I/logs/build-llama.log
fin() { echo "$1" > "$I/logs/build-llama.done"; echo "$(date "+%F %T") $1" >> "$L"; exit 0; }
[ -e "$I/logs/build-llama.done" ] && mv "$I/logs/build-llama.done" "$I/logs/build-llama.done.prev"
{
  echo "$(date "+%F %T") start"
  if [ ! -d "$S/.git" ]; then git clone --depth 200 https://github.com/ggml-org/llama.cpp "$S" || exit 11; fi
  git -C "$S" log --oneline -1
  grep -rl "inkling2" "$S/src" | head -5
} >> "$L" 2>&1 || fin "FAIL clone"
grep -rqi "inkling2" "$S/src" || fin "FAIL this checkout has no inkling2 support"
# nvcc needs cudafe++, which the slim toolkit lacks; a copy (not a link) from the V4.1 build environment lives in $I/toolbin
mkdir -p "$I/toolbin"; [ -x "$I/toolbin/cudafe++" ] || cp "$V/mamba/envs/build/bin/cudafe++" "$I/toolbin/" || fin "FAIL cudafe++ copy"
if [ -d "$B" ] && [ ! -x "$B/bin/llama-server" ]; then mkdir -p "$I/not_used"; mv "$B" "$I/not_used/llama-build.$(date +%H%M%S)"; fi
export PATH=$C/bin:$I/toolbin:$PATH CUDA_HOME=$C CUDA_PATH=$C CUDACXX=$C/bin/nvcc LIBRARY_PATH=$C/lib64 LD_LIBRARY_PATH=$V/rtlibs:$C/lib64
cmake -S "$S" -B "$B" -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=70 \
  -DCMAKE_CUDA_COMPILER=$C/bin/nvcc -DCUDAToolkit_ROOT=$C -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF >> "$L" 2>&1 || fin "FAIL configure"
cmake --build "$B" -j 48 >> "$L" 2>&1 || fin "FAIL build"
[ -x "$B/bin/llama-server" ] || fin "FAIL no llama-server"
fin "OK $(git -C "$S" rev-parse --short HEAD)"
