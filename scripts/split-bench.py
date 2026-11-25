#!/usr/bin/env python3
"""split-bench.py GGUF_FIRST_SHARD [LAYER]

How much work is one card's share of an expert layer for one token, when the layer is cut into 1, 2, 4 or 8
slices? Times the gate/up step and the down step of slice 0 on one card (median of 300 calls, card idle otherwise).
If the time barely falls with more slices, the fixed cost per kernel launch dominates and slicing buys nothing.
"""
import sys, time, statistics as st
import torch
from vllm.models.inkling2.sm70.gguf_experts import Inkling2GGUFExperts

path, L = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 0
E, H, I, TOPK = 384, 4608, 2304, 8
dev = torch.device("cuda:0")
g = torch.Generator().manual_seed(7)
x = (torch.randn(1, H, generator=g) * 0.7).half().to(dev)
ids = torch.randperm(E, generator=g)[:TOPK].reshape(1, TOPK).to(torch.int32).to(dev)
w = torch.ones(1, TOPK, device=dev)


def timed(fn, reps=300):
    for _ in range(30):
        fn()
    torch.cuda.synchronize()
    out = []
    for _ in range(reps):
        t = time.perf_counter(); fn(); torch.cuda.synchronize(); out.append((time.perf_counter() - t) * 1e6)
    return st.median(out)


empty = timed(lambda: x.float().half())
print("one trivial kernel incl. Python and sync: %.0f us (floor of this method)" % empty)
for tp in (1, 2, 4, 8):
    sh = Inkling2GGUFExperts(E, H, I, path, L, tp, 0)
    sh.load(dev)
    act = sh.act_partial(x, ids, 4.0, 25.0)
    a = timed(lambda: sh.act_partial(x, ids, 4.0, 25.0))
    d = timed(lambda: sh.down_partial(act, w, ids))
    native = torch.ops._C_gguf
    op = getattr(native, sh.op13)
    k13 = timed(lambda: op(x, sh.w1, ids, sh.type13, sh.inter_local, TOPK, 1))
    op2 = getattr(native, sh.op2)
    k2 = timed(lambda: op2(act, sh.w2, ids.reshape(-1, 1), sh.type2, sh.rows_local, 1, TOPK))
    print("layer %d cut in %d: gate/up step %4.0f us, down step %4.0f us, sum %4.0f us | bare kernels: one of gate/up %4.0f us, down %4.0f us" % (
        L, tp, a, d, a + d, k13, k2), flush=True)
    del sh
    torch.cuda.empty_cache()
