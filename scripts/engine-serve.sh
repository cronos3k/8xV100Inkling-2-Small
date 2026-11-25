#!/bin/bash
# engine-serve.sh start PROFILE | stop | status | port
# Serve an Inkling-2 model with the SM70 engine build in $I/engine (never the V4.1 tree).
# Profiles: mini (Inkling-2-Mini NVFP4, cards 0-3, TP4: the upstream port as published, Stage 2);
#           small (Inkling-2-Small, 2-bit GGUF experts, all eight cards, TP8, Stage 3);
#           smallpp (the same model split by layer, one run of whole layers per card).
# Port 18142, or the next free one up to 18149; the chosen port is written to $I/run/engine.port.
# Refuses to start while V4.1-Flash or another job holds the cards. Only one model fits at a time.
set -uo pipefail
source "$(dirname "$0")/ink2-env.sh"
R=$I/run; mkdir -p "$R" "$I/cache/triton" "$I/cache/vllm" "$I/cache/torch_extensions"
P=$R/engine.pid; L=$I/logs/engine.log
B=$V/mamba/envs/build; C=$V/cuda-12.8
alive() { [ -e "$P" ] && kill -0 "$(cat "$P")" 2> /dev/null; }
case "${1:-status}" in
  start)
    alive && { echo "already running, pid $(cat "$P")"; exit 0; }
    "$I/bin/v41-guard.sh" || exit 1
    prof=${2:?profile}
    port=""
    for p in 18142 18143 18144 18145 18146 18147 18148 18149; do
      ss -ltn | grep -q ":$p " || { port=$p; break; }
    done
    [ -n "$port" ] || { echo "no free port in 18142-18149"; exit 1; }
    case "$prof" in
      mini)
        name=1616; gpus=${INK2_GPUS:-0,1,2,3}
        args=(--model "$I/models/mini-nvfp4" --served-model-name inkling-2-mini --tensor-parallel-size 4 --dtype half
              --kv-cache-dtype float16 --max-model-len "${INK2_CTX:-65536}" --max-num-batched-tokens 2048 --max-num-seqs 8
              --enable-prefix-caching
              --compilation-config '{"mode":0,"cudagraph_mode":"FULL_DECODE_ONLY","cudagraph_capture_sizes":[1,2,4,8]}'
              --reasoning-parser inkling --tool-call-parser inkling --enable-auto-tool-choice) ;;
      small)
        # Inkling-2-Small, experts 2-bit from the Unsloth GGUF, dense weights from model-dense.safetensors, text only, TP8.
        name=1616; gpus=${INK2_GPUS:-0,1,2,3,4,5,6,7}
        comp=${INK2_COMPILE:-}
        [ -n "$comp" ] || comp='{"mode":0,"cudagraph_mode":"NONE"}'
        args=(--model "$I/models/small-gguf" --served-model-name inkling-2-small --tensor-parallel-size 8 --dtype half
              --kv-cache-dtype float16 --max-model-len "${INK2_CTX:-32768}" --max-num-batched-tokens 2048 --max-num-seqs 4
              --limit-mm-per-prompt '{"image":0}'
              --compilation-config "$comp"
              --reasoning-parser inkling --tool-call-parser inkling --enable-auto-tool-choice) ;;
      smallpp)
        # Inkling-2-Small split by layer: every card owns whole layers (VLLM_PP_LAYER_PARTITION), the block
        # stack is handed from card to card. Card order follows the double NVLink connections.
        name=1616; gpus=${INK2_GPUS:-1,0,2,3,7,6,4,5}
        export VLLM_PP_LAYER_PARTITION=${INK2_PARTITION:-6,6,6,6,6,7,6,5}
        comp=${INK2_COMPILE:-}
        [ -n "$comp" ] || comp='{"mode":0,"cudagraph_mode":"NONE"}'
        args=(--model "$I/models/small-gguf" --served-model-name inkling-2-small --tensor-parallel-size 1
              --pipeline-parallel-size 8 --dtype half
              --kv-cache-dtype float16 --max-model-len "${INK2_CTX:-32768}" --max-num-batched-tokens "${INK2_CHUNK:-2048}"
              --max-num-seqs "${INK2_SEQS:-4}"
              --limit-mm-per-prompt '{"image":0}'
              --compilation-config "$comp"
              --reasoning-parser inkling --tool-call-parser inkling --enable-auto-tool-choice) ;;
      *) echo "unknown profile $prof"; exit 2 ;;
    esac
    VENV=$I/engine/venv-$name
    export PATH=$VENV/bin:$C/bin:$I/toolbin:$B/bin:$PATH
    export CUDA_HOME=$C CUDA_PATH=$C CC=x86_64-conda-linux-gnu-gcc CXX=x86_64-conda-linux-gnu-g++
    export LD_LIBRARY_PATH=$V/rtlibs:$C/lib64 CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=$gpus
    export XDG_CONFIG_HOME=$I/cache/config TRITON_CACHE_DIR=$I/cache/triton FLASHINFER_WORKSPACE_BASE=$I/cache
    export VLLM_CACHE_ROOT=$I/cache/vllm TORCH_EXTENSIONS_DIR=$I/cache/torch_extensions TMPDIR=$I/cache/tmp
    export VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
    export VLLM_WORKER_MULTIPROC_METHOD=spawn OMP_NUM_THREADS=1 VLLM_USE_SPINLOOP_EXT=1
    mkdir -p "$TMPDIR"
    [ -e "$L" ] && mv "$L" "$L.prev"
    cd "$R"
    setsid nohup "$VENV/bin/python" -m vllm.entrypoints.openai.api_server "${args[@]}" \
      --host 127.0.0.1 --port "$port" ${ENGINE_EXTRA:-} > "$L" 2>&1 < /dev/null &
    echo $! > "$P"; echo "$port" > "$R/engine.port"
    echo "started $prof, pid $(cat "$P"), port $port, cards $gpus, log $L" ;;
  stop)
    if alive; then kill -TERM -- "-$(cat "$P")" 2> /dev/null || kill -TERM "$(cat "$P")"; echo "stop sent to $(cat "$P")"; else echo "not running"; fi ;;
  status)
    if alive; then echo "running, pid $(cat "$P"), port $(cat "$R/engine.port" 2> /dev/null)"; else echo "not running"; fi
    [ -e "$R/engine.port" ] && curl -s -m 3 -o /dev/null -w "health %{http_code}\n" "http://127.0.0.1:$(cat "$R/engine.port")/health" ;;
  port) cat "$R/engine.port" ;;
  *) echo "usage: $0 start PROFILE | stop | status | port"; exit 2 ;;
esac
