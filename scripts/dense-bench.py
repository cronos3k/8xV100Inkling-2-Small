#!/usr/bin/env python3
"""dense-bench.py   One token through the dense attention weights of one Small layer (about 200 MB fp16):
time on one card for the whole matrices against an eighth of them. Whole / eighth near 8 means the card is
limited by how fast it can read memory, so slicing over eight cards really is eight times faster there."""
import time, statistics as st
import torch
dev = torch.device("cuda:0")
H = 4608
x = torch.randn(1, H, device=dev).half()

def timed(fn, reps=400):
    for _ in range(40):
        fn()
    torch.cuda.synchronize()
    out = []
    for _ in range(reps):
        t = time.perf_counter(); fn(); torch.cuda.synchronize(); out.append((time.perf_counter() - t) * 1e6)
    return st.median(out)

floor = timed(lambda: x + 1)
print("floor of this method (one trivial kernel): %.0f us" % floor)
for name, rows in (("q or r projection or wo (6144 x 4608)", 6144), ("all dense weights of a layer as one matrix (21700 x 4608, 200 MB)", 21700)):
    for cut in (1, 8):
        w = torch.randn(rows // cut, H, device=dev).half()
        mb = w.numel() * 2 / 2**20
        t = timed(lambda: torch.mm(x, w.t()))
        s = timed(lambda: w.float().sum()) if cut == 1 and rows == 6144 else None
        print("%-66s cut in %d: %6.1f MB, %6.0f us, net %5.0f us -> %4.0f GB/s" % (name, cut, mb, t, t - floor, mb / 1024 / ((t - floor) / 1e6)))
        del w
