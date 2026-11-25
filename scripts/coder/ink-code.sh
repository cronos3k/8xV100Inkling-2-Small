#!/bin/bash
# OpenCode in the terminal on the box, connected to Inkling-2-Small.
#   ink-code.sh                 in the current directory
#   ink-code.sh <project dir>   in that directory
#   ink-code.sh run "task"      one task without the interface
source "$(dirname "$0")/ink-common.sh"
llm_answers || { echo "Inkling does not answer on port $(llm_port). Run: $INK/ink-start.sh"; exit 1; }
sed -i "s#\"baseURL\": *\"[^\"]*\"#\"baseURL\": \"http://127.0.0.1:$(llm_port)/v1\"#" "$INK/opencode.json"
mkdir -p "$INK/term/config" "$INK/term/data" "$INK/term/state" "$INK/term/cache"
export OPENCODE_CONFIG=$INK/opencode.json OPENCODE_DISABLE_AUTOUPDATE=1
export XDG_CONFIG_HOME=$INK/term/config XDG_DATA_HOME=$INK/term/data XDG_STATE_HOME=$INK/term/state XDG_CACHE_HOME=$INK/term/cache
exec "$V41/bin/opencode" "$@"
