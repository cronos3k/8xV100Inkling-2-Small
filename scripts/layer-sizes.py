#!/usr/bin/env python3
"""layer-sizes.py GGUF_FIRST DENSE_SAFETENSORS [PARTS]

Bytes each decoder layer needs on a card (packed experts from the GGUF + dense weights), and the contiguous
split into PARTS cards (default 8) with the smallest largest card. Embedding counts for the first card, output
head for the last.
"""
import json, re, struct, sys
from vllm.models.inkling2.sm70.gguf_experts import gguf_index

gguf, dense, parts = sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8
t = gguf_index(gguf)
n = 48
size = [0] * n
for L in range(n):
    for k in ("ffn_gate_up_exps", "ffn_down_exps"):
        size[L] += t["blk.%d.%s.weight" % (L, k)].data.nbytes
with open(dense, "rb") as f:
    hl = struct.unpack("<Q", f.read(8))[0]
    head = json.loads(f.read(hl))
other = {}
for name, m in head.items():
    if name == "__metadata__":
        continue
    b = m["data_offsets"][1] - m["data_offsets"][0]
    if m["dtype"] == "BF16" or m["dtype"] == "F16":
        pass
    mo = re.search(r"\.layers\.(\d+)\.", name)
    if mo:
        size[int(mo.group(1))] += b
    else:
        key = "embed" if ".embed." in name else "unembed" if "unembed" in name else "rest"
        other[key] = other.get(key, 0) + b
G = 2**30
print("per layer GiB:", " ".join("%.2f" % (s / G) for s in size))
print("other GiB:", {k: round(v / G, 2) for k, v in other.items()})
first, last = other.get("embed", 0) + other.get("rest", 0), other.get("unembed", 0) + other.get("rest", 0)
# dynamic programme: minimise the largest card over contiguous splits
import functools
pre = [0]
for s in size:
    pre.append(pre[-1] + s)

@functools.lru_cache(None)
def best(i, k):
    """layers i.. into k cards -> (max bytes, split tuple)"""
    if k == 1:
        return (pre[n] - pre[i] + last + (first if i == 0 else 0), (n - i,))
    out = None
    for j in range(i + 1, n - k + 2):
        here = pre[j] - pre[i] + (first if i == 0 else 0)
        rest = best(j, k - 1)
        cand = (max(here, rest[0]), (j - i,) + rest[1])
        if out is None or cand[0] < out[0]:
            out = cand
    return out

mx, split = best(0, parts)
print("best split:", ",".join(map(str, split)), " largest card %.2f GiB" % (mx / G))
i = 0
for c, k in enumerate(split):
    b = pre[i + k] - pre[i] + (first if c == 0 else 0) + (last if c == parts - 1 else 0)
    print("  card %d: layers %2d-%2d  %.2f GiB" % (c, i, i + k - 1, b / G))
    i += k
i = 0
ev = [n // parts] * parts
print("even split 6x8: " + " ".join("%.2f" % ((pre[6 * c + 6] - pre[6 * c] + (first if c == 0 else 0) + (last if c == parts - 1 else 0)) / G) for c in range(8)))
