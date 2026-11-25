#!/usr/bin/env python3
"""apply_pp_aux.py WORKTREE

After apply_pp.py: carry the drafter features (aux hidden states of the layers the DSpark drafter reads) across
the hand-off between pipeline stages, so the drafter can run on the last stage as in the V4.1 PP2 x TP4 setup.
Hand-off gains "ink2_aux" [tokens, n, hidden] when aux layers lie before the stage. Marker INK2-PPAUX.
"""
import os, sys

path = os.path.join(sys.argv[1], "vllm", "models", "inkling2", "sm70", "model.py")
s = open(path).read()
if "INK2-PPAUX" in s:
    print("already patched: sm70/model.py (aux)")
    sys.exit(0)
PAIRS = [
    ("""        carried: torch.Tensor | None = None,
    ) -> torch.Tensor | tuple[torch.Tensor, list[torch.Tensor]]:""",
     """        carried: torch.Tensor | None = None,
        aux_in: torch.Tensor | None = None,  # INK2-PPAUX
    ) -> torch.Tensor | tuple[torch.Tensor, list[torch.Tensor]]:"""),
    ("""        aux_hidden_states = []
        top_blocks""",
     """        aux_hidden_states = [] if aux_in is None else list(aux_in.unbind(1))
        top_blocks"""),
    ("""            return stack[: num_blocks + 1].transpose(0, 1).contiguous()""",
     """            return (
                stack[: num_blocks + 1].transpose(0, 1).contiguous(),
                torch.stack(aux_hidden_states, 1) if aux_hidden_states else None,
            )"""),
    ("""            carried = intermediate_tensors["hidden"]
            inputs_embeds = None""",
     """            carried = intermediate_tensors["hidden"]
            aux_in = intermediate_tensors.tensors.get("ink2_aux")
            inputs_embeds = None"""),
    ("""        carried = None
        if intermediate_tensors is not None:""",
     """        carried = aux_in = None
        if intermediate_tensors is not None:"""),
    ("""        out = self.model(positions, inputs_embeds, carried)
        if self.pp_size > 1 and not self.model.pp_last:
            return IntermediateTensors({"hidden": out})
        return out""",
     """        out = self.model(positions, inputs_embeds, carried, aux_in)
        if self.pp_size > 1 and not self.model.pp_last:
            stack, aux = out
            tensors = {"hidden": stack}
            if aux is not None:
                tensors["ink2_aux"] = aux
            return IntermediateTensors(tensors)
        return out"""),
    ("""        blocks = -(-self.model.start_layer // self.model.block_size) + 1
        return IntermediateTensors(
            {
                "hidden": torch.zeros(
                    (batch_size, blocks, self.text_config.hidden_size),
                    dtype=dtype,
                    device=device,
                )
            }
        )""",
     """        blocks = -(-self.model.start_layer // self.model.block_size) + 1
        hidden = self.text_config.hidden_size
        tensors = {
            "hidden": torch.zeros((batch_size, blocks, hidden), dtype=dtype, device=device)
        }
        num_aux = sum(
            1 for a in self.model.aux_hidden_state_layers if a < self.model.start_layer
        )
        if num_aux:
            tensors["ink2_aux"] = torch.zeros(
                (batch_size, num_aux, hidden), dtype=dtype, device=device
            )
        return IntermediateTensors(tensors)"""),
]
for old, new in PAIRS:
    if s.count(old) != 1:
        raise SystemExit("sm70/model.py: expected exactly one match, found %d, for:\n%s" % (s.count(old), old))
    s = s.replace(old, new)
open(path, "w").write(s)
print("patched: sm70/model.py (aux hand-off)")
