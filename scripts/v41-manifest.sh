#!/bin/bash
# v41-manifest.sh write|check
# Fingerprint of the V4.1-Flash installation, taken without writing anything into it.
#   write : store the reference fingerprint (refuses to overwrite an existing one)
#   check : fingerprint again and compare with the reference
# Part 1 (.sha)   sha256 of every file under 200 MB that defines the build and the service.
# Part 2 (.sizes) size of every other file (weights, venv, toolchain).
# Left out on purpose, because V4.1 itself rewrites them while running: state/, cache/, logs/, __pycache__/, .git/.
set -uo pipefail
source "$(dirname "$0")/ink2-env.sh"
M=$I/manifest; mkdir -p "$M"
gen() {
  {
    find "$V/engine/src-pp2" "$V/engine/run-pp2" "$V/repo" "$V/modelhome" "$V/build.sh" "$V/build2.sh" \
      \( -name .git -o -name __pycache__ -o -name state -o -name cache -o -name logs \) -prune -o \
      -type f -size -200M -print0
    find "$HOME/coder" -maxdepth 1 -type f -print0
  } | sort -z | xargs -0 sha256sum > "$1.sha"
  find "$V/models" "$V/modelhome" "$V/engine/.venv-pp2" "$V/engine/wheel" "$V/cuda-12.8" "$V/rtlibs" "$V/mamba" "$V/tools" \
    \( -name __pycache__ -o -name .cache \) -prune -o -type f -printf "%s %p\n" | sort -k2 > "$1.sizes"
}
case "${1:-}" in
  write)
    [ -e "$M/v41.sha" ] && { echo "reference exists: $M/v41.sha (not overwritten)"; exit 1; }
    gen "$M/v41"; date "+%F %T" > "$M/v41.date"
    echo "reference written: $(wc -l < "$M/v41.sha") checksums, $(wc -l < "$M/v41.sizes") sizes" ;;
  check)
    [ -e "$M/v41.sha" ] || { echo "no reference yet; run: $0 write"; exit 2; }
    t=$M/check.$$; gen "$t"; rc=0
    diff "$M/v41.sha" "$t.sha" > "$t.dsha" || rc=1
    diff "$M/v41.sizes" "$t.sizes" > "$t.dsizes" || rc=1
    if [ $rc = 0 ]; then echo "V4.1 manifest UNCHANGED ($(wc -l < "$t.sha") checksums, $(wc -l < "$t.sizes") sizes; reference of $(cat "$M/v41.date"))"
    else echo "V4.1 manifest DIFFERS:"; head -20 "$t.dsha" "$t.dsizes"; cp "$t.dsha" "$M/last-diff.sha"; cp "$t.dsizes" "$M/last-diff.sizes"; fi
    mkdir -p "$I/not_used"; mv "$t.sha" "$t.sizes" "$t.dsha" "$t.dsizes" "$I/not_used/" 2>/dev/null
    exit $rc ;;
  *) echo "usage: $0 write|check"; exit 2 ;;
esac
