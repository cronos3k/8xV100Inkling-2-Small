# Hugging Face post

Attach `../figures/00-header-server.png` first, then `../figures/01-speed-ladder.png` and `../figures/03-layouts.png`.
Hugging Face posts render Markdown, so the table below works as written.

---

**Welcome to Volta Wonderland: Inkling-2-Small (594B) on eight Tesla V100s from 2017**

I got `thinkingmachines/Inkling-2-Small` running on 8x V100-SXM2-32GB at 90–113 tok/s on code, with the full 1,048,576-token context window. Not in llama.cpp, but in a Volta (SM70) build of vLLM, from the Unsloth `UD-IQ2_XXS` GGUF.

| | Measured |
|---|---|
| Code generation, one stream, with the bundled draft model | 90–113 tok/s |
| Without draft model, one stream / four parallel | ~50 / up to 145 tok/s |
| llama.cpp, same file, same cards | 15 tok/s |
| Context window | 1,048,576 tokens (retrieval tested to 56K so far) |
| 16 executed coding tasks, 2-bit weights, thinking off | 13 passed |
| Prompt intake | ~300 tok/s on long prompts (the open problem) |

What it took:

- **Experts stay packed.** The 384 experts per layer are kept in their IQ2/IQ3 codec on the cards and computed directly from it; only the dense weights are expanded.
- **CUDA graphs:** 7 → 41 tok/s, identical answers.
- **Exchange latency, not bandwidth.** One token is about 150 small all-reduces across the cards. NCCL needs 31–40 µs each; a measured NVLink route needs 6–8 µs. 41 → 50 tok/s.
- **The bundled DSpark draft model:** seven drafts per pass, four to seven accepted on code. 50 → 90–113 tok/s. On prose it gains nothing.

The result I did not expect: splitting the model by layer, one block of six layers per card, moves far less data between cards than slicing every matrix eight ways, and is still less than half as fast (21 vs 50 tok/s). Each token reads about 265 MB of weights per layer, one V100 reads about 700 GB/s, and by layer only one card reads at a time. Tensor parallelism wins on old cards for the plain reason that it lets all of them read memory at once.

Not solved: prompt intake is slow, memory at 1M context is at the edge of the cards, and the draft model does not yet work properly in a two-board (2 × 4 cards) layout.

Paper with every measurement and the wrong turns, all benchmark scripts and the engine patches:
https://github.com/cronos3k/8xV100Inkling-2-Small

Built on vLLM and the 1Cat Volta build of it (including its Inkling-2-Mini port), the Unsloth quantisation, llama.cpp as the reference, and OpenCode as the interface. Thanks to all of them, and to Thinking Machines for the model and its draft model.
