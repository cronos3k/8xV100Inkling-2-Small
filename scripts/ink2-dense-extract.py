#!/usr/bin/env python3
"""ink2-dense-extract.py GGUF_FIRST_SHARD NAMEMAP_JSON HEADERS_JSON OUT_DIR [--verify CHECKPOINT_DIR] [--no-write]

Turn every non-expert tensor of an Inkling-2 GGUF back into the original checkpoint's name, shape and dtype and
write them to OUT_DIR/model-dense.safetensors (+ model.safetensors.index.json), so the engine's ordinary
safetensors loader can load them unchanged. The routed experts (ffn_gate_up_exps / ffn_down_exps) stay in the GGUF.

NAMEMAP_JSON: from ink2-namemap.py (GGUF name -> checkpoint name + transform the converter applied).
HEADERS_JSON: {checkpoint name: {dtype, shape}} (st-headers.py, or --local mode of it).
--verify DIR: compare every extracted tensor with the tensor of the same name in DIR/*.safetensors.
Run with PYTHONPATH=<llama.cpp>/gguf-py and a Python that has torch + safetensors (the engine venv).
"""
import glob, json, os, re, sys, time
import numpy as np
import torch
import gguf
from gguf import quants

A = [x for x in sys.argv[1:] if not x.startswith("--")]
first, namemap, headers, out = A[0], json.load(open(A[1]))["table"], json.load(open(A[2])), A[3]
verify = next((sys.argv[i + 1] for i, x in enumerate(sys.argv) if x == "--verify"), None)
if verify:
    A = [x for x in A if x != verify]
write = "--no-write" not in sys.argv
DT = {"BF16": torch.bfloat16, "F32": torch.float32, "F16": torch.float16}

shards = sorted(glob.glob(re.sub(r"-\d{5}-of-(\d{5})\.gguf$", r"-*-of-\1.gguf", first)))
tensors = {}
for s in shards:
    for t in gguf.GGUFReader(s).tensors:
        tensors[t.name] = t

ref = {}
if verify:
    from safetensors import safe_open
    for f in sorted(glob.glob(os.path.join(verify, "model*.safetensors"))):
        h = safe_open(f, "pt")
        for k in h.keys():
            ref[k] = (h, k)

os.makedirs(out, exist_ok=True)
result, t0, worst, nbytes = {}, time.time(), [], 0
for g, m in sorted(namemap.items()):
    hf = m["hf"]
    if ".mlp.experts." in hf:
        continue
    t = tensors[g]
    a = quants.dequantize(np.asarray(t.data), t.tensor_type)          # numpy order = reversed GGUF dims
    x = torch.from_numpy(np.ascontiguousarray(a, dtype=np.float32))
    tr = m["transform"]
    if tr == "T":
        x = x.T
    elif tr == "flip0_T":
        x = x.T.flip(0)                                               # converter: flip(0).T
    elif tr != "none":
        raise SystemExit("unknown transform %s for %s" % (tr, g))
    want = headers[hf]
    shape = tuple(want["shape"])
    if x.numel() != int(np.prod(shape)) if shape else x.numel() != 1:
        raise SystemExit("%s -> %s: %s cannot become %s" % (g, hf, tuple(x.shape), shape))
    if tuple(x.shape) != shape:
        # only a dropped or added unit axis is allowed (the converter squeezes conv weights)
        if [d for d in x.shape if d != 1] != [d for d in shape if d != 1]:
            raise SystemExit("%s -> %s: shape %s is not %s up to unit axes" % (g, hf, tuple(x.shape), shape))
        x = x.reshape(shape)
    y = x.contiguous().to(DT[want["dtype"]])
    if not torch.isfinite(y).all():
        raise SystemExit("%s: non-finite values after conversion" % hf)
    if verify and hf in ref:
        h, k = ref[hf]
        r = h.get_tensor(k).float()
        d = (y.float() - r).abs().max().item()
        worst.append((d, r.abs().max().item(), hf))
    result[hf] = y
    nbytes += y.numel() * y.element_size()
print("%d dense tensors, %.2f GB, %.0f s" % (len(result), nbytes / 1e9, time.time() - t0), flush=True)
if verify:
    worst.sort(reverse=True)
    bad = [w for w in worst if w[0] > 0]
    print("verified %d tensors against %s: %d differ at all; largest absolute differences:" % (len(worst), verify, len(bad)))
    for d, mx, n in worst[:8]:
        print("   %.3e (largest |value| %.3e)  %s" % (d, mx, n))
if write:
    from safetensors.torch import save_file
    save_file(result, os.path.join(out, "model-dense.safetensors"), metadata={"format": "pt"})
    json.dump({"metadata": {"source_gguf": os.path.basename(first)}, "weight_map": {k: "model-dense.safetensors" for k in sorted(result)}},
              open(os.path.join(out, "model.safetensors.index.json"), "w"), indent=1)
    print("wrote", os.path.join(out, "model-dense.safetensors"))
