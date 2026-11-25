#!/usr/bin/env python3
"""cmp-ref.py DIR_A DIR_B   Compare two oracle-ref.py runs token by token."""
import json, os, sys
a, b = sys.argv[1], sys.argv[2]
same = 0
def toks(d):
    c = d["response"]["choices"][0]
    lp = (c.get("logprobs") or {}).get("content")
    return [t["token"] for t in lp] if lp else list(c["message"]["content"])
names = [f for f in sorted(os.listdir(a)) if f.endswith(".json") and os.path.exists(os.path.join(b, f))]
for f in names:
    tx, ty = toks(json.load(open(os.path.join(a, f)))), toks(json.load(open(os.path.join(b, f))))
    n = next((i for i, (p, q) in enumerate(zip(tx, ty)) if p != q), None)
    if n is None and len(tx) == len(ty):
        same += 1; print("%-10s identical (%d tokens)" % (f[:-5], len(tx)))
    else:
        print("%-10s first difference at token %s of %d / %d" % (f[:-5], n, len(tx), len(ty)))
print("identical: %d of %d" % (same, len(names)))
