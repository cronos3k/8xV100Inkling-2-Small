#!/usr/bin/env python3
"""apply_pp.py WORKTREE

Split Inkling-2 by layer instead of slicing every matrix (1Cat-vLLM PR #1616, after apply.py):
each pipeline stage (card) owns a contiguous run of whole decoder layers. The hand-off between two cards is
the block-residual stack the next layer mixes over: the finished 6-layer blocks plus the running one,
[tokens, blocks + 1, hidden] in fp16 (at most 9 x 4608 values per token). Embedding on the first card,
output head on the last. Layer counts per card: VLLM_PP_LAYER_PARTITION.
Exact string replacements, each must match once; marker INK2-PP; safe to re-run.
"""
import os, sys

path = os.path.join(sys.argv[1], "vllm", "models", "inkling2", "sm70", "model.py")
s = open(path).read()
if "INK2-PP" in s:
    print("already patched: sm70/model.py")
    sys.exit(0)
PAIRS = [
    # imports
    ("""from vllm.sequence import IntermediateTensors
""",
     """from vllm.sequence import IntermediateTensors
from vllm.distributed import get_pp_group  # INK2-PP
from vllm.distributed.utils import get_pp_indices  # INK2-PP
from vllm.model_executor.models.utils import PPMissingLayer  # INK2-PP
"""),
    # the model owns only its stage's layers
    ("""        self.embed_tokens = VocabParallelEmbedding(
            config.padded_vocab_size, config.hidden_size
        )
        self.embed_norm = Inkling2RMSNorm(config.hidden_size, config.rms_norm_eps)
        self.layers = nn.ModuleList(
            self._make_layer(config, i, quant_config, f"{prefix}.layers.{i}")
            for i in range(config.num_hidden_layers)
        )
""",
     """        # INK2-PP: one contiguous run of whole layers per pipeline stage (card).
        pp = get_pp_group()
        self.pp_first, self.pp_last = pp.is_first_rank, pp.is_last_rank
        self.start_layer, self.end_layer = get_pp_indices(
            config.num_hidden_layers, pp.rank_in_group, pp.world_size
        )
        self.embed_tokens = (
            VocabParallelEmbedding(config.padded_vocab_size, config.hidden_size)
            if self.pp_first
            else PPMissingLayer()
        )
        self.embed_norm = (
            Inkling2RMSNorm(config.hidden_size, config.rms_norm_eps)
            if self.pp_first
            else PPMissingLayer()
        )
        self.layers = nn.ModuleList(
            self._make_layer(config, i, quant_config, f"{prefix}.layers.{i}")
            if self.start_layer <= i < self.end_layer
            else PPMissingLayer()
            for i in range(config.num_hidden_layers)
        )
"""),
    # forward: start from the embedding or from the carried stack, run own layers, hand the stack on
    ("""    def forward(
        self, positions: torch.Tensor, inputs_embeds: torch.Tensor
    ) -> torch.Tensor | tuple[torch.Tensor, list[torch.Tensor]]:
        \"\"\"Non-looped checkpoints (upstream's non-fused path).\"\"\"
        num_tokens, hidden = inputs_embeds.shape
        aux_hidden_states = []
        num_layers = len(self.layers)
        max_blocks = -(-num_layers // self.block_size)
        stack = inputs_embeds.new_empty((max_blocks + 1, num_tokens, hidden))
        stack[0].copy_(inputs_embeds)
        num_blocks = 0
        tau = self._log_scaling_tau(positions)
        for i, layer in enumerate(self.layers):
            partial = stack[num_blocks]
""",
     """    def forward(
        self,
        positions: torch.Tensor,
        inputs_embeds: torch.Tensor | None,
        carried: torch.Tensor | None = None,
    ) -> torch.Tensor | tuple[torch.Tensor, list[torch.Tensor]]:
        \"\"\"Non-looped checkpoints (upstream's non-fused path).

        INK2-PP: a later pipeline stage starts from `carried`
        `[tokens, blocks + 1, hidden]` (finished blocks and the running one);
        every stage but the last returns that stack for the next one.\"\"\"
        aux_hidden_states = []
        top_blocks = -(-self.end_layer // self.block_size)
        if carried is None:
            assert inputs_embeds is not None
            num_tokens, hidden = inputs_embeds.shape
            stack = inputs_embeds.new_empty((top_blocks + 1, num_tokens, hidden))
            stack[0].copy_(inputs_embeds)
            num_blocks = 0
        else:
            num_tokens, have, hidden = carried.shape
            num_blocks = have - 1
            stack = carried.new_empty((top_blocks + 1, num_tokens, hidden))
            stack[:have].copy_(carried.transpose(0, 1))
        tau = self._log_scaling_tau(positions)
        for i in range(self.start_layer, self.end_layer):
            layer = self.layers[i]
            partial = stack[num_blocks]
"""),
    ("""        out = self._mix(
            stack[:num_blocks], stack[num_blocks], self.attn_res.output_query, self.norm
        )[0]
""",
     """        if not self.pp_last:
            # INK2-PP: hand the block stack to the next card.
            return stack[: num_blocks + 1].transpose(0, 1).contiguous()
        out = self._mix(
            stack[:num_blocks], stack[num_blocks], self.attn_res.output_query, self.norm
        )[0]
"""),
    # wrapper: allow the split for non-looped checkpoints, head only on the last card
    ("""        assert vllm_config.parallel_config.pipeline_parallel_size == 1
""",
     """        self.pp_size = vllm_config.parallel_config.pipeline_parallel_size  # INK2-PP
"""),
    ("""            model_cls = Inkling2LoopModel
""",
     """            assert self.pp_size == 1, "looped Inkling2 checkpoints are not split by layer"
            model_cls = Inkling2LoopModel
"""),
    ("""        self.lm_head = ParallelLMHead(
            text_config.padded_vocab_size, text_config.hidden_size
        )
""",
     """        self.lm_head = (
            ParallelLMHead(text_config.padded_vocab_size, text_config.hidden_size)
            if get_pp_group().is_last_rank
            else PPMissingLayer()
        )
"""),
    ("""    has_own_embed_tokens = False
""",
     """    has_own_embed_tokens = False
    supports_pp = True  # INK2-PP

    def make_empty_intermediate_tensors(
        self, batch_size: int, dtype: torch.dtype, device: torch.device
    ) -> IntermediateTensors:
        \"\"\"Input of a later stage: the block stack as the previous card leaves it.\"\"\"
        blocks = -(-self.model.start_layer // self.model.block_size) + 1
        return IntermediateTensors(
            {
                "hidden": torch.zeros(
                    (batch_size, blocks, self.text_config.hidden_size),
                    dtype=dtype,
                    device=device,
                )
            }
        )
"""),
    ("""        if inputs_embeds is None:
            assert input_ids is not None
            inputs_embeds = self.model.embed_input_ids(input_ids)
        return self.model(positions, inputs_embeds)
""",
     """        carried = None
        if intermediate_tensors is not None:  # INK2-PP: a later stage
            carried = intermediate_tensors["hidden"]
            inputs_embeds = None
        elif inputs_embeds is None:
            assert input_ids is not None
            inputs_embeds = self.model.embed_input_ids(input_ids)
        out = self.model(positions, inputs_embeds, carried)
        if self.pp_size > 1 and not self.model.pp_last:
            return IntermediateTensors({"hidden": out})
        return out
"""),
    # weights of layers that live on another card are skipped
    ("""                if m is not None and int(m.group(2)) >= layer_limits[m.group(1)]:
                    continue
""",
     """                if m is not None and int(m.group(2)) >= layer_limits[m.group(1)]:
                    continue
                if self.pp_size > 1:  # INK2-PP: owned by another card
                    if m is not None and m.group(1) == "layers":
                        if not (
                            self.model.start_layer
                            <= int(m.group(2))
                            < self.model.end_layer
                        ):
                            continue
                    elif name.startswith(
                        ("lm_head.", "model.embed_tokens.", "model.embed_norm.")
                    ):
                        continue
"""),
]
for old, new in PAIRS:
    if s.count(old) != 1:
        raise SystemExit("sm70/model.py: expected exactly one match, found %d, for:\n%s" % (s.count(old), old))
    s = s.replace(old, new)
open(path, "w").write(s)
print("patched: sm70/model.py (layer split)")
