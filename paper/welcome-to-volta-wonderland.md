# Welcome to Volta Wonderland: Making Frontier Open-Source Models Run on 8-Year-Old GPUs

**Gregor Koch**

Draft of 2026-11-25. Lines marked `[OPEN: ...]` are results that are not measured yet.

## Abstract

We run Inkling-2-Small, an open-weight mixture-of-experts language model with 594 billion parameters in total and 17 billion active per token, on eight Tesla V100 cards from 2017. The cards have 32 GB each, no bf16, no 8-bit float, and a compute capability (SM70, "Volta") that current inference software has mostly stopped supporting. The model runs from a 2-bit quantised file inside a third-party Volta build of vLLM, not inside llama.cpp, and answers coding tasks at a usable quality.

The first working version generates about 50 tokens per second for one stream and up to 145 tokens per second for four parallel requests; llama.cpp on the same file and the same cards reaches 15. With the model's bundled draft model switched on, code generation rises to 90 to 113 tokens per second on one stream, and the full 1,048,576-token context window starts and passes a first retrieval test. This paper is mostly about what we learned on the way there. We measured three ways of spreading the model over eight cards and found that the intuitive arguments for each of them were wrong in at least one respect. We also describe, candidly, the wrong turns we took, because they are the kind a reader coming from current hardware would take as well. The work is not finished: prompt intake is still slow, and packed dense weights, model-specific fused kernels and drafting across two boards are open, and are marked as such.

## 1. Hardware

The machine is a server with eight Tesla V100-SXM2-32GB cards, 503 GB of main memory and 96 CPU threads. The cards were released in 2017.

### 1.1 What the cards can and cannot do

- 32 GB of memory per card, 256 GB in total.
- Half-precision (fp16) tensor cores. No bf16, no fp8, no int8 tensor-core path of the kind newer kernels assume.
- Compute capability 7.0. Several features that newer CUDA kernels rely on are missing, and the Triton compiler lowers its dot product to scalar fp32 arithmetic on this capability (taken from the engine author's notes, section 3).

### 1.2 NVLink

The cards are connected by NVLink 2.0 in the hybrid cube-mesh layout known from the DGX-1. We read the topology and measured it (`scripts/ar-bench.py`):

- All 48 links are up at 25.78 GB/s each, six per card.
- Each card has a direct NVLink connection to four of the other seven: two of them over a double link, two over a single link. The remaining three pairs have no direct link and go over PCIe across the two CPU sockets.
- Cards 0-3 form one fully connected group ("board"), cards 4-7 the other. Each card has one link to its counterpart on the other board.

| Path | Measured copy speed |
|---|---|
| Card to card, double NVLink | 48.2 GB/s |
| Card to card, single NVLink | 24.2 GB/s |
| Card to card, PCIe across sockets | 10.2 GB/s |

### 1.3 Memory read speed

The number that turned out to matter most is how fast one card can read its own memory. We measured it with a half-precision matrix-vector product over matrices of the size the model uses (`scripts/dense-bench.py`): about 620 GB/s on a 54 MB matrix and about 720 GB/s on a 190 MB matrix. We use 700 GB/s as the working figure. The engine author's notes use 750 GB/s as a practical figure for the same card.

## 2. The models

### 2.1 DeepSeek-V4.1-Flash: the reference already on the machine

Before this work, the machine already served DeepSeek-V4.1-Flash from a 2-bit GGUF file as a coding agent, with a context of 1,048,576 tokens. That setup is not ours to take credit for; it is the reference we should have studied first (section 6). Its relevant properties are in section 3.2. One rule held throughout: the V4.1 installation is never modified. A checksum manifest over its tree (`scripts/v41-manifest.sh`, 26,751 checksums) was verified after every stage and never changed.

### 2.2 Inkling-2-Small

Inkling-2-Small (`thinkingmachines/Inkling-2-Small`) is a mixture-of-experts model: every layer has a large bank of small feed-forward networks ("experts"), and a router picks a few of them per token.

- 594 billion parameters in total, about 17 billion active per token.
- 48 decoder layers, hidden size 4608, vocabulary 201,024.
- 384 experts per layer, 8 chosen per token. Each expert has an intermediate size of 2304. The activation is a soft-capped SwiGLU: `gate_cap * tanh(g / gate_cap) * sigmoid(g) * up_cap * tanh(u / up_cap)` with caps 4 and 25.
- 40 of the 48 layers use sliding-window attention over 1024 tokens; every sixth layer attends globally.
- Short causal convolutions (kernel size 4) after attention and after the experts, whose state has to be cached per token.
- **Block attention residuals.** Layers are grouped in blocks of six. The input of every sublayer is a learned mix over the outputs of all finished blocks plus the running one. This matters for any split by layer: a hand-off between two cards has to carry the whole stack of block outputs, not one hidden state.

The original checkpoint is about 390 GB (experts in 4-bit and 8-bit float formats that the V100 has no kernels for). The same vendor publishes Inkling-2-Mini (26.4 billion total, 3.4 billion active, hidden 2304), which we used as a small test vehicle.

## 3. The engine and the work we build on

None of the following is our work. We name it because the result depends on it entirely.

### 3.1 1Cat-vLLM, a Volta build of vLLM

1Cat-vLLM is a third-party fork of the vLLM inference server for SM70 cards. It carries its own CUDA kernels for 2-bit and 4-bit GGUF codecs, its own low-latency exchange between four cards, CUDA-graph decode, and speculative decoding. Pull request #1616 of that project ports Inkling-2-Mini: the model code, about twenty JIT-compiled kernels, and design notes with a careful timing breakdown. We built that pull request from source (`scripts/build-engine.sh`) and ran Mini as published on four cards: 150 tokens per second decode, about 5,300 tokens per second prompt intake, a retrieval test passed at 56,000 tokens.

Two properties of the pull request shape everything below:

- Its fused kernels are compiled for Mini's sizes (128 experts, hidden 2304) and are guarded by shape checks. For Small they do not engage, and the model falls back to general paths.
- It forbids a split by layer with an assertion, and several of its fast paths require exactly four cards.

The engine author's notes for Mini (file `sm70_inkling2_mini_perf_plan.md` in the pull request) state that the unfused Mini port ran 1,839 small kernels per token, about 38 per layer, and was about eight times above the memory-read floor. We quote this because Small is in the same position today.

### 3.2 The V4.1-Flash production setup

The existing V4.1 installation on the machine uses this configuration (read from its profile; none of it measured by us):

- **Two boards of four.** The model is split by layer once, in the middle. Layers 0-19 run on cards 0-3, layers 20-39 with the output head and the draft model on cards 4-7. Inside each board every weight matrix is sliced four ways. In vLLM terms this is pipeline parallel 2 times tensor parallel 4.
- **Native GGUF storage.** Experts, dense weights and the embedding stay in their packed format on the cards. Nothing is expanded to 16 bits.
- **A draft model.** A small bundled model (DSpark) proposes five tokens per round; the large model verifies them in one pass. The installation's log shows 3.6 accepted tokens per pass on average over 270 reporting windows.
- A long list of model-specific kernels and a context of 1,048,576 tokens.

### 3.3 Other inputs

- The 2-bit file is Unsloth's `UD-IQ2_XXS` GGUF of Inkling-2-Small (190.6 GB in five shards). Layers 0-39 use the IQ2_XXS and IQ3_XXS codecs for the experts, layers 40-47 IQ2_S and IQ4_XS.
- llama.cpp, used only as a measuring stick (section 4.2).

## 4. Getting Small to run

### 4.1 Download

The model host limits each connection to about 5 MB/s regardless of authentication. A segmented downloader over a second uplink (`scripts/fetch-seg.py`) averaged about 48 MB/s. Every file was verified by SHA-256.

### 4.2 Are 2-bit weights still good enough?

Before building anything we checked whether a 2-bit Small is worth running. For this one purpose we used llama.cpp on the eight cards. It decodes at 15 tokens per second, which is not usable for an agent; the run only answers the quality question.

- **Reference prompts.** 12 of 12 answered correctly (`scripts/oracle-ref.py`).
- **Long context.** A retrieval ("needle") test passed at 28,088 and at 123,456 prompt tokens (`scripts/needle.py`).
- **Coding, executed.** 16 tasks whose answers are compiled and run (`scripts/codeprobe.py`): an expression evaluator, a TTL cache, SHA-256 from memory, C utilities under sanitizers, an SQL window query, a small Scheme interpreter, an interval tree against brute force, a B-tree and others. With thinking off, 14 of 16 pass. Both failures are single-token slips: one wrong SHA-256 round constant (`0xab47d2c4` for `0xab1c5ed5`) and `Object.is` where `===` was required. Each passes when that one token is corrected.
- **Exact recall** (`scripts/recallprobe.py`). Signal numbers, errno values, well-known ports, the SHA-256 constants and the first half of the AES S-box were reproduced without error. Errors appear in the second half of the S-box (9 of 128 entries), in a CRC table (8 of 32) and after 80 digits of pi. Three further tables could not be scored because of defects in our checker; we report them as unscored.

Our reading: the damage from 2-bit quantisation shows as occasional single wrong tokens in long exact sequences, not as incoherence. That is good enough to build on, and it means the model should be given tools to verify constants rather than be trusted with them.

### 4.3 Dense weights

The engine's GGUF classes could not be used for Inkling as they are: their fast paths are tied to other models' sizes and their activation is fixed. We therefore took the shortest route into the existing Inkling loader: all non-expert tensors are dequantised from the GGUF once, offline, and written under the original checkpoint's names and shapes (`scripts/ink2-namemap.py`, `scripts/ink2-dense-extract.py`; 996 tensors, 13.3 GB). The method was verified on Mini, where the original checkpoint is available: largest absolute difference 3e-8.

This step is one of the wrong turns discussed in section 6. It expands weights stored at 4 to 8 bits to 16 bits.

### 4.4 Experts in their 2-bit codec

The experts stay packed. A new module (`scripts/engine-patch/gguf_experts.py`, applied by `scripts/engine-patch/apply.py`) holds the packed bytes on the card and runs the three projections of an expert (gate, up, down) through the engine's general codec operators, with the soft-capped activation and the weighted sum in plain tensor operations.

When a layer is sliced over several cards ("tensor parallel"), the cut has to respect the codec: every row of a packed matrix consists of blocks of 256 weights, and a block cannot be cut. Gate and up are sliced by rows of the intermediate dimension. The down projection would normally be sliced along its input, but 2304 divided by eight is 288, not a multiple of 256. We slice it by output rows instead and give it the whole activation. The price is one extra exchange between the cards per layer.

A unit test on one card (`scripts/test-gguf-experts.py`) compares the module with a float64 CPU calculation from the same file: cosine similarity 0.99993, relative RMS error 1.1 percent (the 8-bit activation quantisation inherent to the operator), and eight emulated slices identical to one.

### 4.5 First results

Small loads in about 20 seconds per card and uses 23.5 GiB per card when sliced eight ways.

| Version | One stream |
|---|---|
| llama.cpp, eight cards (measuring stick) | 15 tok/s |
| Engine, sliced eight ways, no CUDA graphs | 7-8 tok/s |
| Same with CUDA graphs for decode | about 41 tok/s |

CUDA graphs record the sequence of kernel launches of a decode step once and replay it without going through Python. The answers with and without graphs were identical on all 12 reference prompts. Seven of 12 answers are token-identical to llama.cpp; the other five diverge after 16 to 58 tokens into different but valid wording, which is what different rounding does at near-ties under greedy decoding.

## 5. How to split a model over eight cards

This is the central question of the paper. There are three natural answers, and we built and measured all three.

- **Slice every matrix** ("tensor parallel"). Every layer lives on all cards. Each card holds a slice of every matrix, computes its part, and the cards exchange partial results several times per layer. That exchange is called an all-reduce: every card contributes a tensor, every card receives the sum.
- **Split by layer** ("pipeline parallel"). Each card holds a run of whole layers. A token passes from card to card.
- **Both**: split by layer into two halves and slice inside each half.

### 5.1 The cost of one exchange

Sliced eight ways, one decode token needs roughly 150 exchanges, each carrying only 9 to 37 KB. The 300 GB/s that the NVLink mesh can move per card is irrelevant at that size. What counts is the fixed delay per exchange.

The engine's own fast exchange paths require exactly four cards. With eight it falls back to NCCL, the standard library. We checked NCCL's routing hop by hop in its log: it does stay on NVLink. But it costs 31 to 40 microseconds per call inside the server.

The engine also contains an experimental planner that, at start-up, generates its own routes over the measured topology, times them against the existing backend, and keeps the winner. It is off by default and plans only one message size. We switched it on and extended it to the other sizes that occur (the expert activation, and batches of two and four requests):

| Message size | Planned NVLink route | NCCL |
|---|---|---|
| 9 KB | 6.0 µs | 30.7 µs |
| 18 KB | 7.2 µs | 32.3 µs |
| 37 KB | 7.8 µs | 38.3 µs |
| 74 KB | 9.7 µs | 40.2 µs |
| 147 KB | 29.7 µs | 39.8 µs |

(Numbers from the planner's own start-up measurement, median of nine samples each.)

Effect on Small, sliced eight ways: one stream from about 41 to about 50 tokens per second, four parallel requests from 111 to 145, the coding bench from 148 to 118 seconds with the same 13 of 16 tasks passing. After this change the exchanges are a small part of the time per token.

### 5.2 The argument for splitting by layer

With the exchanges out of the way, we timed one card's share of an expert layer for one token when the layer is cut into 1, 2, 4 or 8 slices (`scripts/split-bench.py`, including about 35 µs of measurement floor per call):

| Expert layer cut in | One gate-or-up kernel | Down kernel |
|---|---|---|
| 1 (whole) | 131-142 µs | 131-142 µs |
| 2 | 97-104 µs | 102-106 µs |
| 4 | 78-84 µs | 87-88 µs |
| 8 | 72-74 µs | 79-82 µs |

An eighth of the work costs more than half the time. The fixed cost per kernel launch dominates, and eight cards buy about a factor of two on this step.

The model's structure seemed to fit a split by layer exactly: 48 layers in blocks of six, eight cards, one block per card. From these two observations we predicted that a split by layer would land somewhat below the sliced version at first and overtake it once the kernels were fused. That prediction was wrong.

### 5.3 Splitting by layer, built and measured

We implemented it (`scripts/engine-patch/apply_pp.py`). Each card owns a run of whole layers; the embedding sits on the first card and the output head on the last. Only the stack of block outputs moves between cards: at most 74 KB per token, in fp16, so the result is the same arithmetic as on one card. Because the last eight layers use larger codecs, an even split would put 29.5 GiB on the last card; the best contiguous split is 6, 6, 6, 6, 6, 7, 6, 5 layers with 25.2 GiB on the fullest card (`scripts/layer-sizes.py`).

It is correct: answers are identical with and without CUDA graphs on 12 of 12 prompts, 8 of 12 are token-identical to the sliced run, and the coding bench passes 15 of 16.

It is also much slower. Per-card timing shows 6.7, 4.9, 4.9, 5.0, 5.2, 6.0, 5.2 and 7.3 ms per token, 45 ms in total, or about 0.82 ms per layer.

### 5.4 Why: bytes per token

The explanation is in what one token has to read.

- **Dense attention weights:** about 190 MB per layer in fp16. Every token reads all of them in every layer.
- **Experts:** about 75 MB per layer for the eight chosen experts, in their 2-bit codec.

That is roughly 265 MB per layer and about 13 GB per token. One card reads about 700 GB/s. We confirmed that the dense part is limited by exactly this (`scripts/dense-bench.py`): a whole layer's dense weights take 260 µs on one card, an eighth of them takes 38 µs, a ratio of 6.8.

So the two parts of a layer behave in opposite ways. The expert kernels are bound by launch overhead and gain little from slicing. The dense weights, 70 percent of the bytes, are bound by memory read speed and gain almost the full factor of eight.

Split by layer, only one card reads at a time. The floor is about 17 ms per token, a ceiling near 55 tokens per second for one stream, whatever the kernels. Sliced eight ways, all cards read at once and the floor is about 2.3 ms. Both figures are estimates from the measured read speed and the byte counts.

### 5.5 Two boards of four

Finally we ran Small in the layout the V4.1 installation uses: one split by layer between the two boards (25 and 23 layers), four-way slicing inside each. The engine's four-card push exchange engaged by itself. Nothing else was tuned.

### 5.6 Results

All rows: Inkling-2-Small, 2-bit experts, dense weights in fp16, CUDA graphs for decode, thinking off, greedy decoding, context limited to 8K for these tests.

| Layout | One stream | Parallel requests, total | Coding bench |
|---|---|---|---|
| llama.cpp (measuring stick) | 15 tok/s | not measured | 14 of 16 |
| Sliced eight ways, NCCL | about 41 tok/s | up to 111 tok/s with four | 13 of 16 |
| Sliced eight ways, planned NVLink route | about 50 tok/s | up to 145 tok/s with four | 13 of 16 |
| Two boards of four, untuned | about 40 tok/s | up to 116 tok/s with four | 14 of 16 |
| Eight single cards by layer | about 21 tok/s | 65 tok/s with eight | 15 of 16 |

The differences in the coding bench between layouts are within what different rounding orders produce; we do not read them as quality differences. One of the three failures on the engine is a "what does this program print" task that the model gets right when it is allowed to think; on the engine, thinking set to off is really off.

The two-board layout is not faster as it stands. Its value is that it is the layout the engine's fused kernels and its draft-model path are written for.

Two boards of four with the draft model are covered in section 5.7; the four-card fused kernels are not yet sized for Small.

### 5.7 Draft model and long context

**Draft model.** Small ships a 3.4 GB draft model that proposes seven tokens per round; the target model checks them in one pass and keeps the ones it agrees with. The engine already contains this path for Inkling. Switched on over eight-way slicing, with no other change (`scripts/small-draft-start.sh`):

| Prompt type, one stream | Without draft model | With draft model |
|---|---|---|
| Code | about 50 tok/s | 90 to 113 tok/s, log windows up to 136 |
| Prose | about 50 tok/s | 39 to 56 tok/s |
| Reference set including prompt time | 48.4 tok/s | 60.7 tok/s |

Acceptance per draft position on code was 0.93, 0.85, 0.80, 0.44, 0.37, 0.36, 0.34: the first three drafts are usually right, the rest less often. On prose about two tokens per pass are kept, so the draft model costs slightly more than it saves. The draft model refuses fewer than seven drafts, its trained block size. The coding bench passes 13 of 16 with it, in 112 s on one stream.

On two boards of four the hand-off was extended to carry the draft model's input features (`scripts/engine-patch/apply_pp_aux.py`). The features match the eight-way run to three digits during prompt intake, and answers are correct, but acceptance of the first draft falls to 10 to 35 percent and code runs at 52 to 56 tok/s. CUDA graphs and the scheduling mode are ruled out as causes. The reference setup handles drafting across its two boards with its own first-board hooks, which this engine tree does not have for Inkling.

**Long context.** The model allows 1,048,576 tokens. The Inkling attention in this engine supports only the unpacked fp16 cache, which costs about 4.75 GiB per card at that length, plus a convolution-state cache that grows with the prompt chunk size. With default settings 788K fits. The full 1M fits with an exact cache size, a 128-token prompt chunk and graphs for one and eight tokens only (`scripts/small-1m-start.sh`); the cards then sit at 32.36 of 32.5 GiB. Two looser settings ran out of memory during start-up.

| At the 1M setting | Measured |
|---|---|
| Cache capacity | 1,107,938 tokens |
| Code generation, one stream | 110.8 tok/s |
| Retrieval test (three hidden codes) | passed at 56,149 prompt tokens |
| Prompt intake | 309 tok/s on that test; up to about 1,350 tok/s on short agent turns |

Prompt intake is the weak point: a full 1M prompt would take close to an hour. Prefix caching limits the damage for an agent, which only adds new tokens each turn. The reference setup takes in about 17,900 tok/s with a dedicated expert intake kernel.

**In use.** The model serves OpenCode through the engine's tool-call parser. A file-writing task with a shell command completed end to end from a workstation over an SSH tunnel, from a terminal on the machine, and through the web interface (`scripts/coder/`).

## 6. Lessons

We write this section candidly because the mistakes are instructive and because a reader arriving from current hardware would likely make the same ones.

**Read the working reference first.** A tuned installation of another model was running on the same machine. Its profile answers, in a few lines, the questions we spent a day on: how to lay the model out, how to store the weights, where the speed comes from. We designed without reading it, and at one point described it incorrectly from a careless search. Everything in section 3.2 was available on day one.

**Eight-way slicing was the textbook choice and the wrong first choice.** It was the quickest way to get the model onto all cards. It is also the one layout in which none of the engine's four-card fast paths can engage. We then repaired its symptoms. The repair (section 5.1) is a real finding, but it answered a question the reference setup never has to ask.

**Do not expand what arrives packed.** Dequantising the dense weights to fp16 was convenient and roughly triples the bytes every token has to read. We then met those bytes again as a "physical limit" in section 5.4. The limit is real for the weights as we stored them; it is partly of our own making.

**Estimate a layout from the whole layer, not from the part you happened to time.** The prediction for the layer split came from the expert kernels alone. The dense weights behave in the opposite way and carry most of the bytes. A one-line calculation of bytes per token against read speed would have shown it before any code was written.

**The transition count was a real problem, then it was not.** Minimising exchanges mattered while each cost 31 to 40 µs. At 6 to 8 µs they stopped setting the speed. An argument can be right for the system as measured yesterday and wrong today.

**Passes per second is not tokens per second.** The reference installation is fast for its user mostly because its draft model lets each pass emit several tokens. Small currently emits one token per pass. Comparing our decode rate with the reference's generation rate, without that distinction, flatters neither correctly.

**The general lesson.** Habits formed on current hardware do not transfer to this machine. Standard answers assume cheap bf16, fused library kernels, fully connected fast links and bandwidth to spare. Here every one of those is different, and the people who built the engine have already found workable answers to most of the resulting problems. The productive order is: look for the existing answer in the engine and in the working setup, transfer it, and only then design something new.

**Smaller practical notes.**

- Never replace a shell script while it runs; the shell reads it incrementally.
- The engine caches per-model capability flags keyed by one file's hash. After changing the model class, the stale entry made the engine refuse a mode the code supported.
- With a split by layer, the convolution-state cache is sized for the prompt chunk times the number of batches in flight. A chunk of 2048 tokens that was fine when sliced did not fit with eight stages.
- At 95 percent memory use with eight parallel requests, the fullest card ran out of memory inside the exchange library and the server hung instead of failing. At 90 percent it ran clean.

## 7. Open work

- **Draft model on two boards.** With the draft model, the two-board layout answers correctly but only 10 to 35 percent of first draft tokens are accepted, against 93 percent with eight-way slicing (section 5.7). `[OPEN: cause and fix]`
- **Packed dense weights.** Load the attention weights in their GGUF codec, as the reference setup does. This would also free about 1 GiB per card, which the 1M context needs. `[OPEN: bytes read per token and decode speed with dense weights kept packed]`
- **Fused kernels for Small's sizes.** Router, attention and the three expert projections in one launch each, following what the engine author did for Mini. `[OPEN: decode speed with fused kernels sized for 384 experts and hidden 4608]`
- **Prompt intake.** The 1,048,576-token context starts and passes a retrieval test at 56,149 tokens, but prompt intake runs at about 300 tokens per second at that setting (section 5.7). `[OPEN: prompt intake speed after a larger chunk and a dedicated expert intake path]` `[OPEN: retrieval test at 1M tokens]`
- **Layout.** Eight-way slicing is the working base today. `[OPEN: final choice once the two-board draft problem and the fused kernels are settled]`
- **Thinking.** At default effort the model thinks for 9,000 to 12,000 tokens on a hard coding task. `[OPEN: coding bench with thinking on at a reduced effort, on the engine]`
- **Vision** is switched off; the tests are text only.
- **Recall probe.** Three tables are unscored because of checker defects.

## 8. Reproduction

All scripts are in `scripts/`; the engine changes are in `scripts/engine-patch/`.

| Step | Files |
|---|---|
| Protect the existing installation | `v41-manifest.sh`, `v41-guard.sh` |
| Download and verify | `fetch.py`, `fetch-seg.py`, `download2.sh` |
| Build the engine from the pull request; build llama.cpp | `build-engine.sh`, `build-llama.sh`, `ink2-env.sh` |
| Measuring-stick server and reference answers | `oracle-serve.sh`, `oracle-ref.py`, `cmp-ref.py`, `needle.py` |
| Quality probes | `codeprobe.py`, `recallprobe.py` |
| Dense weights out of the GGUF | `st-headers.py`, `ink2-namemap.py`, `ink2-dense-extract.py` |
| 2-bit expert module and its unit test | `engine-patch/gguf_experts.py`, `engine-patch/apply.py`, `test-gguf-experts.py` |
| Split by layer | `engine-patch/apply_pp.py`, `patch-serve-pp.py`, `layer-sizes.py` |
| Serving | `engine-serve.sh`, `small-start.sh` (sliced, planned NVLink route), `smallpp-start.sh` (by layer; two boards of four through its override variables) |
| Micro-benchmarks | `ar-bench.py` (exchange latency, link speeds), `split-bench.py` (expert layer cut in 1-8), `dense-bench.py` (memory read speed) |

The patches are exact string replacements against pull request #1616 of 1Cat-vLLM at commit `e8d18b0a2c`; each one stops if its target text is not found exactly once, and each is safe to run twice.

## Acknowledgements

This work stands on the 1Cat-vLLM project and its Inkling-2 port, on the authors of the V4.1-Flash production setup for these cards, on Unsloth's quantised model files, on llama.cpp and its GGUF tooling, and on the vLLM project.
