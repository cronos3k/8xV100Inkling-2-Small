#!/usr/bin/env python3
"""ink2-namemap.py BASE_DIR GGUF_FIRST_SHARD OUT_JSON

Build the exact GGUF -> checkpoint name table for Inkling-2 by running the llama.cpp converter's own
name rules (conversion/inkling2.py + gguf-py tensor map) over the checkpoint's tensor names, then
checking the result against the tensors that are really in the GGUF. Header data only; no weights read.
Run with PYTHONPATH=<llama.cpp>/gguf-py.
"""
import json, os, re, sys, glob
import gguf

base, first, out = sys.argv[1:4]
idx = json.load(open(os.path.join(base, "model.safetensors.index.json")))
names = sorted(idx["weight_map"])
cfg = json.load(open(os.path.join(base, "config.json")))
text = cfg.get("text_config", cfg)
n_layers = text.get("num_hidden_layers") or text.get("n_layers")
tmap = gguf.get_tensor_name_map(gguf.MODEL_ARCH.INKLING2, n_layers)

def conv(name):
    """checkpoint name -> (gguf name, transform) or None, following filter_tensors + modify_tensors."""
    if any(p in name for p in ("visual.", "vision_tower.", "mtp.", "markov_head", "nextn_predict")):
        return None
    if name.endswith(("_weight_scale", "_weight_amax", "_weight_outer_scale_denominator")):
        return None
    name = name.replace("model.language_model.", "model.").replace("model.llm.", "model.")
    name = re.sub(r"attn_res\.attn_queries\.(\d+)", lambda m: "layers.%d.attention_input.query" % (int(m[1]) + 1), name)
    name = name.replace("mlp.gate.bias", "mlp.gate.e_score_correction_bias")
    tr = "none"
    if name.endswith(".w13_weight"):
        name = name.replace(".w13_weight", ".gate_up_proj"); tr = "w13_rows_deinterleaved"
    if name.endswith(".w2_weight"):
        name = name.replace(".w2_weight", ".down_proj")
    for static, c in ((".static_weight", ".conv1d.weight"), (".static_w", ".weight")):
        if name.endswith(static):
            name = name.removesuffix(static) + c; tr = "flip0_T"
    if name.endswith(".rel_logits_proj.proj"):
        tr = "T"
    new = tmap.get_name(name)
    if new is not None:
        return new + (".bias" if name.endswith(".e_score_correction_bias") else ".weight"), tr
    new = tmap.get_name(name, try_suffixes=(".weight", ".bias"))
    if new is None:
        return "UNMAPPED:" + name, tr
    return new, tr

table, unmapped, skipped = {}, [], []
for n in names:
    r = conv(n)
    if r is None:
        skipped.append(n); continue
    g, tr = r
    if g.startswith("UNMAPPED:"):
        unmapped.append(n); continue
    if g in table:
        print("ALIAS", g, table[g]["hf"], n)
    table[g] = {"hf": n, "transform": tr}

shards = sorted(glob.glob(re.sub(r"-\d{5}-of-(\d{5})\.gguf$", r"-*-of-\1.gguf", first)))
have = {}
for s in shards:
    rd = gguf.GGUFReader(s)
    for t in rd.tensors:
        have[t.name] = {"shape": [int(x) for x in t.shape], "type": t.tensor_type.name, "shard": os.path.basename(s)}
missing = sorted(set(have) - set(table)); extra = sorted(set(table) - set(have))
for g, v in have.items():
    if g in table:
        table[g].update(v)
print("checkpoint tensors %d, skipped %d, unmapped %d, mapped %d" % (len(names), len(skipped), len(unmapped), len(table)))
print("gguf tensors %d in %d shards; in gguf but not mapped: %d; mapped but not in gguf: %d" % (len(have), len(shards), len(missing), len(extra)))
for label, lst in (("unmapped", unmapped), ("gguf-only", missing), ("map-only", extra)):
    for x in lst[:25]:
        print("  ", label, x, have.get(x, ""))
json.dump({"table": {g: v for g, v in table.items() if g in have}, "gguf_only": {g: have[g] for g in missing}, "skipped": skipped},
          open(out, "w"), indent=1)
kinds = {}
for g, v in table.items():
    if g in have:
        k = re.sub(r"blk\.\d+\.", "blk.N.", g) + " <- " + re.sub(r"\.\d+(\.|$)", r".N", v["hf"]) + " [" + v["transform"] + "]"
        kinds.setdefault(k, []).append((v["type"], tuple(v["shape"])))
for k in sorted(kinds):
    ts = sorted(set(kinds[k]))
    print("%-4d %s  %s" % (len(kinds[k]), k, "; ".join("%s %s" % (t, "x".join(map(str, s))) for t, s in ts[:4])))
