# shared by the Inkling scripts in this folder. The V4.1-Flash setup in ~/coder is used read-only (its programs),
# never written to: all state, config and logs of the Inkling side live below $I/coder.
I=/srv/archive-a/volta-ink2
INK=$I/coder
V41=$HOME/coder
MODEL=inkling-2-small
STATE=$INK/state
mkdir -p "$STATE" "$INK/logs"
llm_port() { cat "$I/run/engine.port" 2>/dev/null || echo 18142; }
llm_pid()  { cat "$I/run/engine.pid" 2>/dev/null; }
llm_proc_ok() { local p; p=$(llm_pid); [ -n "$p" ] && kill -0 "$p" 2>/dev/null; }
llm_answers() { curl -s -m 5 "http://127.0.0.1:$(llm_port)/v1/models" 2>/dev/null | grep -q "\"$MODEL\""; }
v41_answers() { curl -s -m 5 "http://127.0.0.1:$(cat /srv/archive-a/volta-test/engine/run-pp2/state/port 2>/dev/null || echo 18042)/v1/models" 2>/dev/null | grep -q deepseek; }
free_port() {
  local p
  for p in $(seq "$1" "$2"); do
    ss -ltnH 2>/dev/null | awk '{print $4}' | grep -q ":$p\$" || { echo "$p"; return 0; }
  done
  return 1
}
lan_ips() { ip -4 -o addr show scope global | awk '{print $4}' | cut -d/ -f1; }
svc_ok() {
  local p pat
  p=$(cat "$STATE/$1.pid" 2>/dev/null); [ -n "$p" ] && [ -r "/proc/$p/cmdline" ] || return 1
  case $1 in
    speech)   pat="uvicorn.*app:app" ;;
    opencode) pat="opencode.*serve" ;;
    caddy)    pat="caddy.*run" ;;
  esac
  tr '\0' ' ' < "/proc/$p/cmdline" | grep -q "$pat"
}
