#!/usr/bin/env python3
"""test-gguf-experts.py GGUF_FIRST_SHARD [LAYER ...]

Unit test of Inkling2GGUFExperts on one card, without a server: for each layer, the GPU result (one shard,
and eight tensor-parallel shards whose partials are summed the way the all-reduce does) is compared with a
float64 CPU calculation from the weights dequantised by gguf-py. Layers 0 and 47 together cover the four codecs.
Run with the engine venv and PYTHONPATH=<llama.cpp>/gguf-py.
"""
import sys, time
import numpy as np
import torch
from gguf import quants

from vllm.models.inkling2.sm70.gguf_experts import Inkling2GGUFExperts, gguf_index

path = sys.argv[1]
layers = [int(x) for x in sys.argv[2:]] or [0, 47]
E, H, I, TOPK, GCAP, UCAP = 384, 4608, 2304, 8, 4.0, 25.0
dev = torch.device("cuda:0")
tensors = gguf_index(path)
ok_all = True
for L in layers:
    gu = tensors["blk.%d.ffn_gate_up_exps.weight" % L]
    dn = tensors["blk.%d.ffn_down_exps.weight" % L]
    g = torch.Generator().manual_seed(100 + L)
    for tokens in (1, 3, 70):
        x = (torch.randn(tokens, H, generator=g) * 0.7).half()
        ids = torch.stack([torch.randperm(E, generator=g)[:TOPK] for _ in range(tokens)]).to(torch.int32)
        w = torch.rand(tokens, TOPK, generator=g) + 0.1
        w = (w / w.sum(-1, keepdim=True) * 8.0).float()
        # CPU reference in float64 (only for the small cases; 70 tokens checks the batched path against tp1)
        ref = None
        if tokens <= 3:
            ref = np.zeros((tokens, H))
            xd = x.double().numpy()
            for t in range(tokens):
                for s in range(TOPK):
                    e = int(ids[t, s])
                    w13 = quants.dequantize(np.asarray(gu.data[e]), gu.tensor_type).astype(np.float64)
                    w2 = quants.dequantize(np.asarray(dn.data[e]), dn.tensor_type).astype(np.float64)
                    ga, up = w13[:I] @ xd[t], w13[I:] @ xd[t]
                    act = GCAP * np.tanh(ga / GCAP) / (1 + np.exp(-ga)) * UCAP * np.tanh(up / UCAP)
                    ref[t] += float(w[t, s]) * (w2 @ act)
        res = {}
        for tp in (1, 8):
            t0 = time.time()
            shards = [Inkling2GGUFExperts(E, H, I, path, L, tp, r) for r in range(tp)]
            for sh in shards:
                sh.load(dev)
            t_load = time.time() - t0
            xg, idg, wg = x.to(dev), ids.to(dev), w.to(dev)
            act = sum(sh.act_partial(xg, idg, GCAP, UCAP).float() for sh in shards).half()
            out = sum(sh.down_partial(act, wg, idg).float() for sh in shards)
            res[tp] = out.double().cpu().numpy()
            if tokens == 1:
                torch.cuda.synchronize(); t1 = time.time()
                for _ in range(20):
                    a = shards[0].act_partial(xg, idg, GCAP, UCAP)
                    o = shards[0].down_partial(act, wg, idg)
                torch.cuda.synchronize()
                print("layer %d tp%d: codecs %s/%s, operators %s/%s, load %.1f s, %.2f ms per call of one shard, %.0f MiB per shard" % (
                    L, tp, gu.tensor_type.name, dn.tensor_type.name, shards[0].op13, shards[0].op2, t_load, (time.time() - t1) / 20 * 1e3,
                    sum(t.numel() for t in (shards[0].w1, shards[0].w3, shards[0].w2)) / 2**20), flush=True)
            del shards
            torch.cuda.empty_cache()
        base = ref if ref is not None else res[1]
        scale = np.sqrt((base ** 2).mean())
        e1 = np.sqrt(((res[1] - base) ** 2).mean()) / scale
        e8 = np.sqrt(((res[8] - base) ** 2).mean()) / scale
        cos = float((res[8] * base).sum() / np.sqrt((res[8] ** 2).sum() * (base ** 2).sum()))
        good = e8 < 0.03 and (ref is None or e1 < 0.03)
        ok_all &= bool(good)
        print("layer %d, %2d tokens: rms out %.4f; rms error / rms out: one shard %.2e, eight shards %.2e, cosine %.6f (%s)  %s" % (
            L, tokens, scale, e1, e8, cos, "against CPU float64" if ref is not None else "against one shard", "OK" if good else "MISMATCH"), flush=True)
print("RESULT", "ALL-OK" if ok_all else "FAILED")
