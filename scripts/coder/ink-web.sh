#!/bin/bash
# Web interface (OpenCode voice fork + speech service + HTTPS front) connected to Inkling-2-Small.
# Same parts as ~/coder/web.sh, with own ports, state and data below $I/coder so the V4.1 setup is not touched.
# Usage: ink-web.sh [project-directory]     default: $HOME
# Speech runs on the CPU by default: with the 1M context the cards have no room for Whisper.
source "$(dirname "$0")/ink-common.sh"
WORKDIR=${1:-$HOME}
[ -d "$WORKDIR" ] || { echo "no such directory: $WORKDIR"; exit 1; }
llm_answers || "$INK/ink-start.sh" || exit 1
VOICE=$INK/voice
mkdir -p "$INK/caddy" "$VOICE/config/opencode" "$VOICE/data" "$VOICE/state" "$VOICE/cache"
# the certificate authority of the existing web interface, copied once, so browsers that trust it need no new exception
[ -d "$INK/caddy/pki" ] || { [ -d "$V41/caddy/pki" ] && cp -r "$V41/caddy/pki" "$INK/caddy/pki"; }
cp "$INK/voice-opencode.json" "$VOICE/config/opencode/opencode.json"
sed -i "s#\"baseURL\": *\"[^\"]*\"#\"baseURL\": \"http://127.0.0.1:$(llm_port)/v1\"#" "$VOICE/config/opencode/opencode.json"
[ -s "$STATE/web-token" ] || { (umask 077; head -c 24 /dev/urandom | base64 | tr -d '/+=' > "$STATE/web-token"); }
TOKEN=$(cat "$STATE/web-token")

if ! svc_ok speech; then
  P=$(free_port 47321 47340) || { echo "no free port for the speech service in 47321-47340"; exit 1; }
  NV=$V41/speech/venv/lib/python3.12/site-packages/nvidia
  ( cd "$V41/speech" && \
    SPEECH_MODEL_DIR=$V41/speech/models SPEECH_CPU_THREADS=${SPEECH_CPU_THREADS:-32} OMP_NUM_THREADS=${SPEECH_CPU_THREADS:-32} \
    HF_HOME=$V41/speech/models/huggingface HF_HUB_OFFLINE=1 TMPDIR=/dev/shm \
    SPEECH_DEVICE=${SPEECH_DEVICE:-cpu} SPEECH_COMPUTE=${SPEECH_COMPUTE:-int8} CUDA_VISIBLE_DEVICES=${SPEECH_GPU:-0} \
    LD_LIBRARY_PATH=$NV/cublas/lib:$NV/cudnn/lib:$NV/cuda_nvrtc/lib \
    setsid nohup "$V41/spawn.sh" "$STATE/speech.pid" "$V41/speech/venv/bin/uvicorn" app:app --host 127.0.0.1 --port "$P" --workers 1 --limit-concurrency 4 \
      > "$INK/logs/speech.log" 2>&1 < /dev/null & )
  echo "$P" > "$STATE/speech.port"
fi

if ! svc_ok opencode; then
  P=$(free_port 47341 47360) || { echo "no free port for the OpenCode server in 47341-47360"; exit 1; }
  ( cd "$WORKDIR" && \
    XDG_CONFIG_HOME=$VOICE/config XDG_DATA_HOME=$VOICE/data XDG_STATE_HOME=$VOICE/state XDG_CACHE_HOME=$VOICE/cache \
    OPENCODE_PASSWORD=$TOKEN OPENCODE_DISABLE_AUTOUPDATE=1 \
    setsid nohup "$V41/spawn.sh" "$STATE/opencode.pid" "$V41/voice/bin/opencode" serve --hostname 127.0.0.1 --port "$P" \
      > "$INK/logs/opencode-web.log" 2>&1 < /dev/null & )
  echo "$P" > "$STATE/opencode.port"
fi

if ! svc_ok caddy; then
  P=$(free_port 47543 47562) || { echo "no free port for the HTTPS front in 47543-47562"; exit 1; }
  SITES="https://localhost:$P"
  for ip in $(lan_ips); do SITES="$SITES, https://$ip:$P"; done
  cat > "$STATE/Caddyfile" <<CADDY
{
	admin off
	skip_install_trust
	auto_https disable_redirects
	storage file_system $INK/caddy
}
$SITES {
	tls internal
	encode zstd gzip
	@speech path /speech/*
	handle @speech {
		uri strip_prefix /speech
		reverse_proxy 127.0.0.1:$(cat "$STATE/speech.port")
	}
	handle {
		reverse_proxy 127.0.0.1:$(cat "$STATE/opencode.port") {
			header_up Authorization "Basic $(printf 'opencode:%s' "$TOKEN" | base64 -w0)"
		}
	}
}
CADDY
  chmod 600 "$STATE/Caddyfile"
  ( XDG_DATA_HOME=$INK/caddy XDG_CONFIG_HOME=$INK/caddy \
    setsid nohup "$V41/spawn.sh" "$STATE/caddy.pid" "$V41/bin/caddy" run --config "$STATE/Caddyfile" --adapter caddyfile \
      > "$INK/logs/caddy.log" 2>&1 < /dev/null & )
  echo "$P" > "$STATE/caddy.port"
fi
sleep 3
exec "$INK/ink-status.sh"
