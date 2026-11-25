# SPDX-License-Identifier: Apache-2.0
# ruff: noqa: E501
"""Inkling2 routed experts kept in their GGUF codec (IQ2_XXS, IQ2_S, IQ3_XXS, IQ4_XS, ...) on SM70.

The Unsloth GGUF stores, per layer, `ffn_gate_up_exps` [E, 2I, H] (gate rows first, then up rows) and
`ffn_down_exps` [E, H, I], every row a whole number of 256-weight quantisation blocks.

Tensor-parallel layout, chosen so that no block is cut and none is stored twice:
- gate / up: this rank's `I / tp` rows of the intermediate dimension;
- down: this rank's `H / tp` OUTPUT rows, with the full intermediate input (`I / tp` is not a multiple of 256).
The ranks therefore exchange the activation once (a zero-padded all-reduce) between gate/up and down, and the
result once more: two small all-reduces per layer.

First version: correctness. The projections run on the codec-agnostic `torch.ops._C_gguf` operators
(`admit_moe_fallback`), the activation and the weighted sum in plain torch.
"""

import numpy as np
import torch
from torch import nn

from .ops.moe_ref import softcapped_swiglu

_INDEX: dict[str, dict] = {}


def gguf_index(path: str) -> dict:
    """Name -> reader tensor for all shards of a GGUF (mmap-backed, one index per process)."""
    if path not in _INDEX:
        from vllm.transformers_utils.gguf_files import gguf_shard_paths, gguf_tensor_index

        _INDEX[path] = gguf_tensor_index(gguf_shard_paths(path))
    return _INDEX[path]


class Inkling2GGUFExperts(nn.Module):
    def __init__(
        self,
        num_experts: int,
        hidden: int,
        inter: int,
        gguf_path: str,
        layer_id: int,
        tp_size: int,
        tp_rank: int,
    ) -> None:
        super().__init__()
        assert inter % tp_size == 0 and hidden % tp_size == 0
        self.num_experts, self.hidden, self.inter = num_experts, hidden, inter
        self.tp_size, self.tp_rank = tp_size, tp_rank
        self.inter_local = inter // tp_size
        self.rows_local = hidden // tp_size
        self.gguf_path, self.layer_id = gguf_path, layer_id
        self.w1: torch.Tensor | None = None
        self.w3: torch.Tensor | None = None
        self.w2: torch.Tensor | None = None
        self.type13 = self.type2 = -1
        self.op13 = self.op2 = ""

    def _bank(self, data: np.ndarray, first: int, rows: int, weight_type: int, device) -> torch.Tensor:
        from vllm.model_executor.layers.quantization.gguf_native import (
            empty_guarded_weight,
            pad_weight_tail,
        )

        bank = empty_guarded_weight((self.num_experts, rows, data.shape[2]), weight_type, device)
        step = 32
        for e in range(0, self.num_experts, step):
            part = np.ascontiguousarray(data[e : e + step, first : first + rows])
            bank[e : e + step].copy_(torch.from_numpy(part))
        return pad_weight_tail(bank, weight_type, storage_has_zero_tail=True)

    def load(self, device) -> None:
        from vllm.model_executor.kernels.gguf import admit_moe_fallback
        from vllm.model_executor.layers.quantization.gguf_native import (
            NATIVE_TYPES,
            native_available,
        )
        from vllm.transformers_utils.gguf_tensor_reader import quant_size

        if not native_available():
            raise ValueError("GGUF experts need the packaged vllm._C_gguf operators")
        tensors = gguf_index(self.gguf_path)
        gate_up = tensors[f"blk.{self.layer_id}.ffn_gate_up_exps.weight"]
        down = tensors[f"blk.{self.layer_id}.ffn_down_exps.weight"]
        e, i, h = self.num_experts, self.inter, self.hidden
        self.type13, self.type2 = int(gate_up.tensor_type), int(down.tensor_type)
        for name, tensor, rows, k in (("gate_up", gate_up, 2 * i, h), ("down", down, h, i)):
            value = int(tensor.tensor_type)
            if value not in NATIVE_TYPES:
                raise ValueError(f"layer {self.layer_id} {name}: unsupported GGUF type {value}")
            block, size = quant_size(value)
            want = (e, rows, k // block * size)
            if k % block or tuple(tensor.data.shape) != want or tensor.data.dtype != np.uint8:
                raise ValueError(
                    f"layer {self.layer_id} {name}: packed shape {tuple(tensor.data.shape)} != {want}"
                )
        lo = self.tp_rank * self.inter_local
        self.w1 = self._bank(gate_up.data, lo, self.inter_local, self.type13, device)
        self.w3 = self._bank(gate_up.data, i + lo, self.inter_local, self.type13, device)
        self.w2 = self._bank(down.data, self.tp_rank * self.rows_local, self.rows_local, self.type2, device)
        self.op13 = admit_moe_fallback(self.w1, self.type13, torch.float16).operator
        self.op2 = admit_moe_fallback(self.w2, self.type2, torch.float16).operator

    def act_partial(
        self, x: torch.Tensor, ids: torch.Tensor, gate_cap: float, up_cap: float
    ) -> torch.Tensor:
        """This rank's slice of the activation, zero-padded to `[tokens * top_k, I]`."""
        assert self.w1 is not None and self.w3 is not None
        native = torch.ops._C_gguf
        tokens, top_k = ids.shape
        x = x.contiguous()
        op = getattr(native, self.op13)
        gate = op(x, self.w1, ids, self.type13, self.inter_local, top_k, tokens)
        up = op(x, self.w3, ids, self.type13, self.inter_local, top_k, tokens)
        slots = tokens * top_k
        act = softcapped_swiglu(
            gate.reshape(slots, self.inter_local),
            up.reshape(slots, self.inter_local),
            gate_cap,
            up_cap,
        ).to(x.dtype)
        if self.tp_size == 1:
            return act
        full = x.new_zeros((slots, self.inter))
        lo = self.tp_rank * self.inter_local
        full[:, lo : lo + self.inter_local] = act
        return full

    def down_partial(
        self, act: torch.Tensor, weights: torch.Tensor, ids: torch.Tensor
    ) -> torch.Tensor:
        """This rank's output rows, zero-padded to `[tokens, H]`; the sum over the ranks is the result."""
        assert self.w2 is not None
        tokens, top_k = ids.shape
        slots = tokens * top_k
        down = getattr(torch.ops._C_gguf, self.op2)(
            act.contiguous(), self.w2, ids.reshape(-1, 1), self.type2, self.rows_local, 1, slots
        )
        part = (
            down.reshape(tokens, top_k, self.rows_local).float() * weights.float().unsqueeze(-1)
        ).sum(1)
        if self.tp_size == 1:
            return part.to(act.dtype)
        out = act.new_zeros((tokens, self.hidden))
        lo = self.tp_rank * self.rows_local
        out[:, lo : lo + self.rows_local] = part.to(act.dtype)
        return out

    def forward(
        self,
        x: torch.Tensor,
        weights: torch.Tensor,
        ids: torch.Tensor,
        gate_cap: float,
        up_cap: float,
    ) -> torch.Tensor:
        ids = ids.to(torch.int32).contiguous()
        act = self.act_partial(x, ids, gate_cap, up_cap)
        if self.tp_size > 1:
            from vllm.distributed import tensor_model_parallel_all_reduce

            act = tensor_model_parallel_all_reduce(act)
        return self.down_partial(act, weights, ids)
