# ink2-env.sh: common paths of the Inkling-2 project. Sourced by every script in this folder.
# The V4.1-Flash installation ($V and ~/coder) is READ ONLY for this project.
I=/srv/archive-a/volta-ink2
V=/srv/archive-a/volta-test
export I V
export XDG_CACHE_HOME=$I/cache PIP_CACHE_DIR=$I/cache/pip HF_HOME=$I/hfcache PYTHONDONTWRITEBYTECODE=1
# Fast uplink first (Starlink on enp184s0f1 measured 24.7 MB/s, DSL 6.2 MB/s on 2026-11-25).
INK2_DL_IFACES="${INK2_DL_IFACES:-enp184s0f1 enp97s0f3np3}"
export INK2_DL_IFACES
