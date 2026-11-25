# Inkling-2-Small on the V100 box: plan

Status: plan, 2026-11-24. Nothing downloaded, nothing built, nothing changed on the box.
Target: `thinkingmachines/Inkling-2-Small` (594B total, 17B active, 48 layers, 384 experts, 8 per token)
served on the 8x V100-SXM2-32GB box (`user@v100-box`) the way DeepSeek-V4.1-Flash is served there:
2- to 3-bit GGUF experts resident on the cards, PP2 x TP4, speculative decoding, long context.

## Rule 1: V4.1-Flash stays untouched

- Everything for Inkling lives in a new tree, `/srv/archive-a/volta-ink2/` (2.0 TB free on that array).
  Own engine checkout, own venv (copied, never linked), own caches, own run directory, own port (18142), own pid files.
- `/srv/archive-a/volta-test/` and `~/coder/` are read-only for this project. The CUDA 12.8 toolchain and the
  build environment in `volta-test` are used by path only, never written.
- Before the first step: a manifest of `volta-test` (file list, sizes, checksums of configs and sources; the
  `state/`, `cache/` and `logs/` folders excluded). It is checked again after every stage.
- The Inkling launcher refuses to start while a V4.1 server process exists. It never stops V4.1 by itself.
- The one thing both models share is the eight cards. Only one can be loaded at a time; switching is
  stop one, start the other (V4.1 cold load 3-4 minutes).

## What was measured for this plan (2026-11-24)

| fact | value | source |
|---|---|---|
| V4.1 engine | 1Cat-vLLM at `899e9ed` (#1277) + Volta sPLIt patches 0001-0057 | `volta-test/engine/src-pp2`, `volta-test/repo` |
| V4.1 weights | ISTA-DASLab GSQ-RCO GGUF, IQ2_XXS experts 138 GB; Engram 110 GB in host RAM | sPLIt README |
| V4.1 memory on the cards | 17.2 GiB per card (stage 1), 21.8 GiB (stage 2) | `serve-pp2.log` |
| V4.1 speed history | 99 tok/s as a plain PP2 x TP4 port, 135 tok/s after the levers | sPLIt README |
| Host | 503 GB RAM, 96 threads | `free`, `nproc` |
| Inkling code in the installed engine | none | grep over `src-pp2` |
| Inkling upstream | PRs #1598, #1599, #1600, #1616, all open, all Mini, NVFP4/MXFP8 only, TP2/TP4 verified, PP unverified | GitHub |
| Inkling in llama.cpp | merged (#32217 on 2026-11-14, #32657 on 2026-11-20) | GitHub |
| Unsloth `UD-IQ2_XXS` | 190.6 GB, 5 shards, 1,092 tensors, no drafter tensors, vision in a separate 0.7 GB `mmproj` | GGUF headers read over HTTP |

### What is in the Unsloth 2-bit file

Experts are 98.9 % of the model. Two stacked tensors per layer:

| tensor | shape | layers 0-39 | layers 40-47 |
|---|---|---|---|
| `ffn_gate_up_exps` (gate and up fused) | 4608 x 4608 x 384 | IQ2_XXS | IQ2_S |
| `ffn_down_exps` | 2304 x 4608 x 384 | IQ3_XXS | IQ4_XS |

Attention and other dense weights are Q6_K and Q8_0 (7 B parameters), embedding Q4_K, head Q6_K.
All of these codec names occur in the engine's GGUF code; the fast expert kernels built for V4.1 cover IQ2_XXS only.
The expert intermediate size is 2304, the same as in V4.1.

### Attention and context

40 of 48 layers use a 1,024-token sliding window. Only layers 5, 11, 17, 23, 29, 35, 41, 47 attend globally.
KV for the 8 global layers costs 32 KB per token in fp16: 16 GiB per pipeline stage at 1M tokens, 8 GiB at 512K.

### Memory budget, split at layer 24 (calculated)

| | stage 1, cards 0-3 | stage 2, cards 4-7 |
|---|---|---|
| experts | 20.5 GiB per card | 22.4 GiB per card |
| dense as fp16, head, drafter | about 1 GiB | about 2 GiB |
| free of 31 GiB | about 9.5 GiB | about 6.5 GiB |
| KV at 512K, fp16 | 2 GiB | 2 GiB |
| KV at 1M, fp16 / FP8 | 4 GiB / 2 GiB | 4 GiB / 2 GiB |

512K fits in fp16. 1M on stage 2 needs FP8 KV to leave working memory.

## Which V4.1 steps carry over

| V4.1 step | for Inkling |
|---|---|
| Model port in the engine (1Cat #1277) | Upstream PR family brings the model code; the GGUF side is missing and is ours to write |
| PP2 port (patch 0001, 4,938 lines, + 0028) | Same job again: expert storage per stage, drafter across stages, model runner |
| A/B harness, ms per verify round, bitwise and near-tie gates | Reused as is |
| Model Runner V2, NCCL NVLink-only, CUDA graphs, keep-batch | Engine-level, expected to carry over with small changes |
| MoE sum inside the all-reduce, push path | Carries over; message is 55,296 bytes instead of 61,440 |
| Fast expert kernels, instruction diet, plan fuse (IQ2_XXS) | Port for `gate_up`; a new IQ3_XXS kernel for `down` |
| Attention prologue/epilogue fusion | New code: the attention in Inkling is a different design |
| Coupled drafts, drafter sharding | Depends on the Inkling drafter; technique carries over |
| Prefill expert GEMM | Port; needs the IQ3_XXS variant |
| Engram tables, index scorers, packed-KV hot ring, prefill skip | Do not exist in Inkling; nothing to port |

## Size: three candidates

| | size | expert codecs | note |
|---|---|---|---|
| A. Unsloth `UD-IQ2_XXS` as published | 190.6 GB | 4 | default; runs today in llama.cpp |
| B. Own mix from `Q8_0` + the Unsloth imatrix: IQ2_XXS / IQ3_XXS in all 48 layers | about 181 GB | 2 | half the kernel work, 9 GiB more room, last 8 layers coarser |
| C. Unsloth `UD-IQ3_XXS` | 226 GB | to be read | better weights, context limited to about 256K |

Start with A. Decide A against B in stage 3 from measured divergence, not by guess.

## Stages

Each stage ends at a gate. A failed gate stops the project or changes the size, before more work is spent.

**Stage 0. Fetch and fence.** Create `volta-ink2`, write the V4.1 manifest, download (list below), write the
guard launcher. No GPU time.

**Stage 1. Reference run in llama.cpp.** Build llama.cpp master for SM70 inside `volta-ink2`, load file A on
the 8 cards. Record greedy outputs and log-probabilities for a fixed prompt set, a needle test, and tok/s.
Gate: judge whether the 2-bit model good enough to be worth the port. If not, try C or stop.
This is also the oracle every later stage is compared against.

**Stage 2. Engine base with Mini.** Fresh 1Cat checkout with the Inkling PRs, own venv. Run Inkling-2-Mini
(NVFP4) on 2 and 4 cards and reproduce the published 47 tok/s on two cards. Choose between the #1598 family
and #1616. List which sPLIt patches upstream already contains.
Gate: Mini answers correctly on this box.

**Stage 3. Small, text only, correct before fast.**
- GGUF adapter for `inkling2` (the 32 tensor patterns, fused gate/up, the four expert codecs; dense weights
  to fp16 at load).
- The non-loop model class at 48 layers and 384 experts (in PR #1598, marked unverified).
- PP2 split at layer 24 (a 6-layer block boundary), TP4 per stage, every expert resident.
- Kernel checks against CPU references, end to end against the stage 1 oracle.

Gate: greedy output matches the oracle on the reference set; needle found at 128K. Decide A or B.

**Stage 4. Drafter.** The multi-token head (5 layers, reads layers 5 to 48, so both stages) is not in
the GGUF. Fetch only its tensors from the original repository by byte range, load as a sidecar (PR #1600).
Gate: output identical to decoding without drafts; accepted drafts per round measured.

**Stage 5. Speed levers, in the sPLIt order, one at a time through the A/B harness.**
1. Engine switches: Model Runner V2, NCCL NVLink-only, CUDA graphs, keep-batch, all-reduce push.
2. Expert kernels: fast and diet for IQ2_XXS `gate_up`, new IQ3_XXS `down`, plan fuse.
3. Attention fusions for the Inkling attention.
4. Drafter sharding, coupled drafts.
5. Prefill: expert GEMM.
6. Long context: FP8 KV for the 8 global layers, 512K then 1M.

Gate per lever: faster by a detectable margin and output unchanged, otherwise not adopted.

**Stage 6. Serving and quality.** Tool-call and reasoning parsers (PR #1599), a separate set of launchers
next to the V4.1 ones, optional vision (`mmproj`), divergence against `Q8_0` run on the CPU (386 GB fits in
the 503 GB of RAM), speed table by text kind.

## Downloads once the decision is made

All to `/srv/archive-a/volta-ink2/models/`. All repositories are public; no token needed.

| what | size |
|---|---|
| `unsloth/Inkling-2-Small-GGUF` `UD-IQ2_XXS` + `mmproj-F16` + imatrix | 192 GB |
| `thinkingmachines/Inkling-2-Small`: config, tokenizer, template, drafter tensors only | a few GB |
| Inkling-2-Mini NVFP4 for stage 2 | about 25-30 GB (to be confirmed) |
| optional, stage 3/6: `Q8_0` as quality reference and source for mix B | 386.5 GB |

## Risks

1. Quality of a 2-bit Inkling-2-Small is unknown. Stage 1 answers it for the price of a download.
2. The upstream PRs are three days old, compete with each other and are unmerged. We pin commits.
3. PP2 with a drafter that reads both stages was hard for V4.1 (one admissible split). Expect the same.
4. A V100 port of this family is known to produce only token 0 in one engine (Strata issue #6759).
   That is why the oracle comes first.
5. Speed cannot be predicted. V4.1 started at 31 ms per round as a plain port; Inkling has 48 layers
   instead of 40. The first number comes at the end of stage 3.
6. Development needs the cards, so V4.1 is offline during test windows.

## Done means

Inkling-2-Small answers on `127.0.0.1:18142` (OpenAI API, text, tools, thinking), at least 512K context,
speculative decoding on, a measured speed table, and the `volta-test` manifest unchanged.

---

## Status 2026-11-25 02:45 (box time)

| Stage | State | Result |
|---|---|---|
| 0 fetch and fence | done | 2-bit Small GGUF 190.6 GB, Mini NVFP4, both drafters, all sha256-verified. V4.1 manifest unchanged. |
| 1 reference run (llama.cpp) | done, waits for the quality verdict | 12 of 12 reference prompts correct; 15 tok/s decode; needle PASS at 28K and 123K tokens (prompt 78-117 tok/s). 131K context needs `-b 1024 -ub 128`. Answers in `ref/oracle-iq2/`. |
| 2 engine base with Mini | done | PR #1616 built from source (`engine/venv-1616`). Mini on cards 0-3, TP4: 150 tok/s decode, 5,300 tok/s prefill, needle PASS at 56K. First start 17 min (weight conversion + kernel compile), cached afterwards. |
| 3 Small text-only | next | see design below |

### Stage 3 design (changed after reading the engine code)

The engine's GGUF MoE classes cannot be used as they are: every fast path is locked to the V4.1 or a 512-expert
geometry, the activation is fixed to plain SiLU (Inkling needs the softcapped SwiGLU), the V4.1 adapter accepts only
codecs 16/17/29, and PR #1616 asserts pipeline_parallel_size == 1. So instead of a `gguf_adapters/inkling2.py`:

1. **Dense weights offline.** `ink2-dense-extract.py`: GGUF -> `model-dense.safetensors` under the checkpoint's own
   names and shapes (exact table: `ref/namemap-small.json`, 1092 of 1092 tensors; shapes: `ref/st-headers-small.json`).
   The engine's proven default loader then loads them unchanged. Check: run it on the Mini F16 GGUF
   (`models/gguf/mini-own/`, made with the llama.cpp converter) and compare with Mini's safetensors.
   Later option, no memory cost: fetch the 14.6 GB of original BF16 dense tensors by range requests instead.
2. **Experts in the Inkling MoE module.** New `Inkling2GGUFExperts` in `sm70/moe.py`: packed GGUF bytes on the card,
   fused gate_up split by rows (gate `[:2304]`, up `[2304:]`), TP slice by rows (gate/up) and by `packed_tp_span`
   (down), projections through the codec-agnostic `torch.ops._C_gguf` operators (`admit_moe_fallback`), softcapped
   SwiGLU between them, `gguf_original_expert_reduce` at the end. Format switch through `hf_quant_config.json`
   (key `gguf`).
3. **Topology.** TP8 first (fits: about 24 GiB weights per card). PP2xTP4 only if TP8 turns out slower; it needs the
   block-residual stack shipped between stages.
4. **Test loop at Mini scale first** (loads in a minute, four cards): Mini F16 GGUF and a Mini GGUF quantised to the
   same four codecs, engine against llama.cpp on the same file, then Small against `ref/oracle-iq2/`.

Lessons: never replace a script on the box while it runs (it stopped build-engine.sh after the install step);
`python -m vllm.entrypoints.openai.api_server` takes `--model`, not a positional path; Mini still thinks with
reasoning_effort none, so parity tests should use pre-rendered prompts on /v1/completions.

## Status 2026-11-25 03:50 (box time): Stage 3 reached, Small runs on the engine

- 2-bit quality verdict (llama.cpp, then switched off for good): 14 of 16 executed coding tasks pass with thinking off
  (`scripts/codeprobe.py`, answers in `ref/probe/`); both failures single-token slips. Exact recall mostly intact
  (`scripts/recallprobe.py`); default thinking effort is very long (9-12K tokens per task), use a lower effort for the agent.
- Dense weights: `bin/ink2-dense-extract.py` -> `models/small-gguf/model-dense.safetensors` (996 tensors, 13.3 GB),
  verified on Mini against the original checkpoint (max difference 3e-8).
- Engine patch: `scripts/engine-patch/` (`apply.py WORKTREE` + `gguf_experts.py`), applied to `engine/wt-1616`.
  Unit test `bin/test-gguf-experts.py`: all four codecs run on `ggml_moe_mmvq`, cosine 0.99993 against CPU float64,
  eight shards identical to one shard.
- `engine-serve.sh start small` (TP8, all eight cards): loads in 20 s per card, 23.5 GiB per card, answers correctly.
  7 of 12 reference answers token-identical to llama.cpp, the other 5 diverge at near-ties after 16-58 tokens.
  Needs `INK2_CTX=8192 ENGINE_EXTRA="--gpu-memory-utilization 0.95 --max-num-batched-tokens 512"` for now.
- Speed of this first version: 7-8 tok/s (no CUDA graphs, general kernels). llama.cpp: 15. Target: far above both.

Known limits to remove next (Stage 5/6):
1. Speed: CUDA graphs off; the PR's fused kernels (router, attention, MoE) are compiled for Mini's sizes
   (E=128, H=2304) and fall back to general paths for Small; experts run as three separate mmvq launches per layer
   with plain-torch activation and reduce.
2. Context: the conv-state cache costs a fixed ~6 GiB per card at --max-num-batched-tokens 2048 (head size rounded
   up to 16384 per token with the whole hidden replicated on each of 8 ranks); the real KV is only ~3.7 KB per token
   and card. Fix the conv-state layout or keep the prefill chunk small.
3. No drafter (mtp.safetensors) yet, no vision.

## Status 2026-11-25 08:26 box time: NVLink and the all-reduce

Question: is the NVLink mesh used? Measured (`bin/ar-bench.py`, `logs/ar-bench-tp8.log`):
- All 48 links up at 25.78 GB/s. DGX-1 style mesh: each card has NVLink to 4 of the other 7 (two double, two single);
  the remaining 3 pairs go over PCIe across the sockets. Raw copy: 48 GB/s double link, 24 GB/s single, 10 GB/s PCIe.
- At TP8 the fork's fast collectives (SM70_RING, HC_LL, TP4 push) are off: they need exactly four ranks. Fallback is NCCL,
  whose rings do run over NVLink only (checked hop by hop in the NCCL log), but cost about 31-40 us per call.
- A decode token moves 9-37 KB per all-reduce, about 150 of them per token. Latency matters, bandwidth does not.
- Fix: `--kernel-config {"topology_all_reduce":{"enabled":true}}` (the fork's measured route planner, any rank count) plus
  `VLLM_INK2_AR_WIDTHS=18432,36864,73728,147456` (new patch in topology_all_reduce/startup.py; the planner otherwise only
  covers 2 x hidden bytes). Its NVLink route measured 6.0 / 7.2 / 7.8 / 9.7 / 29.7 us against NCCL 30.7 / 32.3 / 38.3 / 40.2 / 39.8 us
  for 9 / 18 / 37 / 74 / 147 KB. First start measures 46 s per size, cached in cache/topology-selections afterwards.
- Result (`bin/small-start.sh topo`, now the way to start Small): single stream about 41 -> 50 tok/s (reference set
  38.5 -> 48.4 tok/s including prompt time), four parallel requests 111 -> up to 145 tok/s, coding bench again 13 of 16,
  148 s -> 118 s. 8 of 12 reference answers token-identical to the NCCL run, 4 diverge late (other summation order).
- Collectives are now about 1 ms of roughly 20 ms per token. The rest is compute: the three separate expert launches per
  layer and the general (not Small-sized) router/attention kernels. That is the next work item, then context, then drafter.

## Status 2026-11-25 08:50 box time: how to split the model

Today: tensor parallel 8. Every layer on every card, every matrix cut in eight, 3-4 exchanges per layer.
Measured on one idle card, one token (`bin/split-bench.py`, includes about 35 us of Python/sync floor per call):

| expert layer cut in | one gate-or-up kernel | down kernel |
|---|---|---|
| 1 (whole) | 131-142 us | 131-142 us |
| 2 | 97-104 us | 102-106 us |
| 4 | 78-84 us | 87-88 us |
| 8 | 72-74 us | 79-82 us |

An eighth of the work costs more than half the time: fixed cost per launch dominates. Slicing in eight buys about 2x
wall time on the expert step for 8x hardware.

Model structure (sm70/model.py): layers are tied by block attention residuals, block = 6 layers
(`n_layers_per_attn_res_block`), so 48 layers = 8 blocks = one block per card. A hand-off at a block border carries the
stack of finished block outputs (at most 9 x 4608 fp16 = 83 KB per token). The port forbids pipeline split by an assert
(model.py:392); the generic one-tensor hand-off would not carry the stack.

Direction: one block of six whole layers per card, chain along NVLink (0-1-3-2-6-7-5-4-0). Open points: memory is uneven
(layers 40-47 use the larger codecs, about 4.6 GiB per layer against 3.5), single stream uses one card at a time, so
speed must come from whole-expert fused kernels and the drafter (several tokens per pass), not from more cards.
V4.1-Flash on this box also runs tensor parallel 8; untouched.

## Status 2026-11-25 10:15 box time: split by layer implemented and measured

Implemented (`scripts/engine-patch/apply_pp.py`, marker INK2-PP in sm70/model.py; profile `smallpp` in engine-serve.sh,
start with `bin/smallpp-start.sh`): each card owns a run of whole layers (6,6,6,6,6,7,6,5, largest card 25.2 GiB,
`bin/layer-sizes.py`), embedding on the first card, output head on the last, hand-off = block stack
[tokens, blocks+1, 4608] fp16 under the key "hidden" (the runner insists on that name). Card order 1,0,2,3,7,6,4,5
follows the double NVLink connections. Pitfalls: stale model-info cache (`cache/vllm/modelinfos`, moved to not_used),
conv-state cache is sized for chunk x batches in flight (8 with the pipeline), so chunk 512; util 0.95 with 8 sequences
ran the 7-layer card out of memory (NCCL error, hang), 0.90 works.

Correct: 12 of 12 answers identical with and without CUDA graphs, 8 of 12 token-identical to the sliced run,
coding bench 15 of 16.

Speed (CUDA graphs):

| | sliced 8 ways + NVLink route | by layer |
|---|---|---|
| one stream | about 50 tok/s | about 21 tok/s |
| 4 parallel | up to 145 tok/s | not measured |
| 8 parallel | not measured | 65 tok/s |

Per-card GPU time per token (VLLM_V41_STEP_TIMING=1): 6.7 / 4.9 / 4.9 / 5.0 / 5.2 / 6.0 / 5.2 / 7.3 ms = 45 ms,
about 0.82 ms per layer.

Why: one token reads every dense attention weight of every layer (about 190 MB fp16 per layer, 9.6 GB in all) plus
the eight chosen experts (about 75 MB per layer). One V100 reads about 700 GB/s (`bin/dense-bench.py`: whole dense
layer 260 us, an eighth 38 us, ratio 6.8). By layer only one card reads at a time: floor about 17 ms per token,
ceiling about 55 tok/s for one stream. Sliced, all eight read at once: floor about 2.3 ms. My earlier estimate
looked only at the expert kernels (launch-bound, slicing gains 2x) and missed the dense weights (bandwidth-bound,
slicing gains 6.8x).

Sliced mode rechecked after the patch: 12 of 12 identical to before, 48.4 tok/s.

Next levers, both layouts: (1) keep the dense weights in their 4-8 bit GGUF codec instead of expanding them to fp16
(2-3x fewer bytes per token); (2) fused kernels sized for Small (router, attention, experts in one launch);
(3) drafter.

## Status 2026-11-25 11:00 box time: reference read, new direction, drafter on

Read the V4.1-Flash production setup (run-pp2: serve-pp2.yaml, rec.env). It is PP2 x TP4 (one split between the two
NVLink boards, four-way slicing inside each), GGUF loaded natively with dense, embedding and expert storage "original",
DSpark drafter with 5 drafts (mean acceptance 3.6 in its log), Model Runner V2, context 1,048,576. My earlier note that
it runs TP8 was wrong.

Small in the same layout (smallpp-start.sh with INK2_EXTRA="--tensor-parallel-size 4 --pipeline-parallel-size 2",
INK2_PARTITION=25,23, cards 0-7 in order): push all-reduce engages by itself; untuned 40 tok/s single, 116 tok/s x4,
coding bench 14 of 16.

Drafter (engine's own Inkling DSpark port, mtp.safetensors copied next to the model, VLLM_USE_V2_MODEL_RUNNER=1,
--speculative-config {"method":"dspark","num_speculative_tokens":7}; `bin/small-draft-start.sh`), sliced 8 ways:
works first try. Code prompts 90-113 tok/s single stream, log windows up to 136 tok/s at acceptance 6.9; prose
39-56 tok/s (acceptance falls to about 2); reference set 60.7 tok/s including prompt time; coding bench 13 of 16 in
112 s with one stream.

Order of work from here (reference first):
1. drafter in the two-board layout (needs the aux hidden states carried over the hand-off), metadata-free hand-off;
2. dense weights loaded packed from the GGUF the way V4.1 does (dense_storage original);
3. expert kernels: transfer V4.1's fast routed-expert path to Small's shape;
4. context: packed KV / conv-state sizing as in the reference; target 1M;
5. paper (`paper/`) and public repository.

## Status 2026-11-25 15:00 box time: drafter on two boards runs, acceptance broken (open)

`scripts/engine-patch/apply_pp_aux.py` carries the drafter features (aux layers 5,11,17,23,29,35,41 + final) over the
hand-off as "ink2_aux"; `bin/small-b2-start.sh [DRAFTS]` starts PP2 x TP4 (25 + 23 layers) with the drafter on board 2.
It runs and answers correctly, but acceptance is 0.1-0.35 at the first position (0.93 sliced 8 ways), so code runs at
52-56 tok/s instead of 90-113.

Ruled out: features in prefill (identical to the TP8 run to 3 digits, VLLM_INK2_DEBUG_AUX=1), CUDA graphs (same
without), scheduling mode (--no-async-scheduling same), VLLM_PP_KEEP_BATCH (refused under Model Runner V2).
Suspects, both from the reference: (1) draft/sampled token transport to the first stage (v1/worker/gpu/pp_utils.py
PPHandler, slot ring delayed by pipeline depth); (2) first-stage per-step state for rejected drafts: the V4.1 tree has
commit hooks pp_before_forward / pp_after_forward (models/deepseek_v41/pp_commit.py) that the Inkling model lacks.
Next: log the token ids each stage embeds per step against the drafts stage 2 verifies.

Best working configuration right now: `bin/small-draft-start.sh` (sliced 8 ways + NVLink route + drafter).

## Status 2026-11-25 16:10 box time: 1M context starts; prompt intake is the blocker

Model allows 1,048,576 (config). Inkling attention on this engine: fp16 KV only (attention.py:362). Need per card for
1M: about 4.75 GiB KV + chunk x 3 MiB conv-state; at chunk 512 that is 6.25 GiB against 5.13 available at util 0.95
(fits 788K). Letting the pool take all memory (util 0.96-0.975) ran out of memory at graph capture and hung the server
(needed kill -KILL of the process group). Working: `bin/small-1m-start.sh` = exact --kv-cache-memory-bytes 5637144576,
chunk 128, graph sizes [1,8], drafter 7 (DSpark refuses fewer than its block size 7). Pool 1,107,938 tokens,
cards at 32.36 GiB.

At that setting: code 110.8 tok/s (unchanged), retrieval test PASS at 56,149 prompt tokens, but prompt intake only
309 tok/s (llama.cpp 78-116, Mini on this engine about 5,300, V4.1 about 17,900). A 1M prompt would take about an
hour. Next: prompt intake (chunk size is held down by memory; expert prefill runs the general path), and freeing
about 1 GiB per card by loading dense weights packed.
