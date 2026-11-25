#!/bin/bash
# build-engine.sh NAME GIT-REF
# Check out GIT-REF of 1Cat-vLLM into $I/engine/wt-NAME and build it for SM70 into $I/engine/venv-NAME
# (editable install, the upstream build-from-source recipe; environment as in the V4.1 build2.sh, new paths).
# Compilers, uv and the CUDA 12.8 toolkit of the V4.1 tree are used by path only; nothing is written there.
# Start detached. Log: $I/logs/build-engine-NAME.log   Result: $I/logs/build-engine-NAME.done (OK ... or FAIL ...)
set -uo pipefail
source "$(dirname "$0")/ink2-env.sh"
name=$1; ref=$2
E=$I/engine; G=$E/src-ink2; SRC=$E/wt-$name; VENV=$E/venv-$name; PY=$VENV/bin/python
L=$I/logs/build-engine-$name.log; D=$I/logs/build-engine-$name.done
B=$V/mamba/envs/build; C=$V/cuda-12.8
fin() { echo "$1" > "$D"; echo "$(date "+%F %T") $1" >> "$L"; exit 0; }
step() { echo "$(date "+%F %T") == $1" >> "$L"; }
[ -e "$D" ] && mv "$D" "$D.prev"
mkdir -p "$I/toolbin" "$I/cache/uv" "$I/cache/torch_extensions" "$I/uv-python"
[ -x "$I/toolbin/cudafe++" ] || cp "$B/bin/cudafe++" "$I/toolbin/" || fin "FAIL cudafe++ copy"
[ -x "$I/toolbin/uv" ] || cp "$B/bin/uv" "$I/toolbin/" || fin "FAIL uv copy"
export PATH=$VENV/bin:$C/bin:$I/toolbin:$B/bin:$PATH
export CUDA_HOME=$C CUDA_PATH=$C CUDA_TOOLKIT_ROOT_DIR=$C CUDAToolkit_ROOT=$C CUDACXX=$C/bin/nvcc
export CC=x86_64-conda-linux-gnu-gcc CXX=x86_64-conda-linux-gnu-g++ CUDA_VISIBLE_DEVICES=""
export LIBRARY_PATH=$C/lib64 LD_LIBRARY_PATH=$V/rtlibs:$C/lib64
export TORCH_CUDA_ARCH_LIST=7.0 CMAKE_CUDA_ARCHITECTURES=70 VLLM_TARGET_DEVICE=cuda MAX_JOBS=32 NVCC_THREADS=1 UV_LINK_MODE=copy
export CMAKE_ARGS="-DCUDA_TOOLKIT_ROOT_DIR=$C -DCUDAToolkit_ROOT=$C -DCMAKE_CUDA_COMPILER=$C/bin/nvcc"
export UV_PYTHON_INSTALL_BIN=0   # no python3.12 link in ~/.local/bin
export UV_CACHE_DIR=$I/cache/uv UV_PYTHON_INSTALL_DIR=$I/uv-python TORCH_EXTENSIONS_DIR=$I/cache/torch_extensions
step "worktree $ref"
if [ ! -d "$SRC" ]; then git -C "$G" worktree add --detach "$SRC" "$ref" >> "$L" 2>&1 || fin "FAIL worktree"; fi
git -C "$SRC" log --oneline -1 >> "$L" 2>&1
step venv
if [ ! -x "$PY" ]; then
  uv python install 3.12 >> "$L" 2>&1 || fin "FAIL python install"
  uv venv --python-preference only-managed --python 3.12 "$VENV" >> "$L" 2>&1 || fin "FAIL venv"
fi
step "editable install (native build)"
( cd "$SRC" && uv pip install --python "$PY" -e . --torch-backend=cu128 ) >> "$L" 2>&1 || fin "FAIL install"
step "import check"
( cd "$I" && CUDA_VISIBLE_DEVICES="" "$PY" -c "import torch, vllm, vllm._C; print(torch.__version__, torch.version.cuda, vllm.__version__, vllm.__file__)" ) >> "$L" 2>&1 || fin "FAIL import"
fin "OK $(git -C "$SRC" rev-parse --short HEAD)"
