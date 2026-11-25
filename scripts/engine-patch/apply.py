#!/usr/bin/env python3
"""apply.py WORKTREE

Add the GGUF expert path to the Inkling2 SM70 port (1Cat-vLLM PR #1616) in WORKTREE:
  sm70/gguf_experts.py   new module (copied from next to this script)
  quant_config.py        hf_quant_config.json may carry {"gguf": {"path": "<first shard>"}}
  sm70/moe.py            third expert implementation "gguf"; the reference router is called by its real name
  sm70/model.py          layers ask the quant config for the expert format
  topology_all_reduce/startup.py   VLLM_INK2_AR_WIDTHS=bytes,bytes,... adds message sizes to the measured NVLink routes
Every edit is an exact string replacement that must match once; the script stops otherwise. Safe to re-run.
"""
import os, shutil, sys

wt = sys.argv[1]
base = os.path.join(wt, "vllm", "models", "inkling2")
here = os.path.dirname(os.path.abspath(__file__))


def edit(rel, pairs):
    path = os.path.join(base, rel)
    s = open(path).read()
    if "INK2-GGUF" in s:
        print("already patched:", rel)
        return
    for old, new in pairs:
        if s.count(old) != 1:
            raise SystemExit("%s: expected exactly one match, found %d, for:\n%s" % (rel, s.count(old), old))
        s = s.replace(old, new)
    open(path, "w").write(s)
    print("patched:", rel)


shutil.copyfile(os.path.join(here, "gguf_experts.py"), os.path.join(base, "sm70", "gguf_experts.py"))
print("copied: sm70/gguf_experts.py")

edit("quant_config.py", [
    ("""        self.mxfp8_weights: set[str] = set()
        for group in config["model"]["parameter_groups"]:""",
     """        self.mxfp8_weights: set[str] = set()
        # INK2-GGUF: experts taken from a GGUF file instead of the checkpoint.
        self.gguf_path: str | None = (config.get("gguf") or {}).get("path")
        for group in config["model"]["parameter_groups"]:"""),
])

edit(os.path.join("sm70", "moe.py"), [
    ("""from .ops.moe_ref import ExpertWeights, dequant_mxfp8, experts_forward
""",
     """from .ops.moe_ref import ExpertWeights, dequant_mxfp8, experts_forward
from .ops.moe_ref import route as _ref_route  # INK2-GGUF
"""),
    ("""QuantFormat = Literal["nvfp4", "mxfp8"]""", """QuantFormat = Literal["nvfp4", "mxfp8", "gguf"]"""),
    ("""        if _BACKEND == "ref":
            self.impl = "ref"
            self.experts = Inkling2Experts(num_experts, hidden, inter, fmt)""",
     """        if fmt == "gguf":
            import re

            from .gguf_experts import Inkling2GGUFExperts

            self.impl = "gguf"
            layer_id = int(re.search(r"layers\\.(\\d+)\\.", prefix + ".").group(1))
            self.experts = Inkling2GGUFExperts(
                num_experts,
                hidden,
                inter,
                quant_config.gguf_path,
                layer_id,
                self.tp_size,
                self.tp_rank,
            )
        elif _BACKEND == "ref":
            self.impl = "ref"
            self.experts = Inkling2Experts(num_experts, hidden, inter, fmt)"""),
    ("""    def inkling_post_load(self) -> None:
        if self.impl == "dense":
            # VLLM_INKLING2_SM70_MXFP8_FUSE: scratch of the route-only launch.""",
     """    def inkling_post_load(self) -> None:
        if self.impl == "gguf":
            self.experts.load(self.gate.weight.device)
            return
        if self.impl == "dense":
            # VLLM_INKLING2_SM70_MXFP8_FUSE: scratch of the route-only launch."""),
    ("""            weights, ids = route(
                x, self.gate.weight, self.gate.bias, self.top_k, self.route_scale
            )
        if self.impl == "turbomind":""",
     """            weights, ids = _ref_route(
                x, self.gate.weight, self.gate.bias, self.top_k, self.route_scale
            )
        if self.impl == "gguf":
            out = self.experts(x, weights, ids, self.gate_cap, self.up_cap)
        elif self.impl == "turbomind":"""),
])

edit(os.path.join("sm70", "model.py"), [
    ("""        self.mlp = Inkling2MoE(
            config, expert_format, quant_config, prefix=f"{prefix}.mlp"
        )""",
     """        if quant_config is not None and getattr(quant_config, "gguf_path", None):
            expert_format = "gguf"  # INK2-GGUF
        self.mlp = Inkling2MoE(
            config, expert_format, quant_config, prefix=f"{prefix}.mlp"
        )"""),
])

edit(os.path.join("..", "..", "distributed", "device_communicators", "topology_all_reduce", "startup.py"), [
    ("""    if any(w <= 0 or w % 16 for w in widths):
        raise ValueError("Unsupported activation width")""",
     """    # INK2-GGUF: further message sizes in bytes (expert activation exchange, small batches).
    import os

    widths |= {int(w) for w in os.environ.get("VLLM_INK2_AR_WIDTHS", "").split(",") if w}
    if any(w <= 0 or w % 16 for w in widths):
        raise ValueError("Unsupported activation width")"""),
])
