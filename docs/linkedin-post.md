# LinkedIn post

Images to attach, in this order (LinkedIn shows them as a swipeable set):
1. `../figures/00-header-server.png` (the header: the server itself; `00-header-server-1200.png` is the same at 1200 x 628)
   `../figures/00-title-card.png` is the plain alternative without the photo
2. `../figures/01-speed-ladder.png`
3. `../figures/04-nvlink-mesh.png`
4. `../figures/02-exchange-latency.png`
5. `../figures/03-layouts.png`

LinkedIn does not render tables, so the table below is written as aligned lines; the images carry the rest.

---

**Welcome to Volta Wonderland: a 594-billion-parameter model on eight GPUs from 2017**

I have eight Tesla V100 cards in a rack. They came out in 2017. They have no bf16, no 8-bit float, and most current inference software has quietly dropped them.

This week they started running Inkling-2-Small, an open model with 594 billion parameters, at 90 to 113 tokens per second on code. With a 1,048,576-token context window. As a working coding assistant.

The numbers, all measured:

▪ Code generation, one stream: 90–113 tok/s
▪ Four requests in parallel: up to 145 tok/s in total
▪ llama.cpp, same file, same cards: 15 tok/s
▪ Context window: 1,048,576 tokens
▪ Weights: 2-bit, and still 13 of 16 on a bench of executed coding tasks

How it got from 15 to about 100:

1️⃣ A purpose-built Volta engine instead of a general one. The model's 384 experts stay in their 2-bit packing on the cards and are computed directly from it.

2️⃣ CUDA graphs. From 7 to 41 tok/s with identical answers.

3️⃣ The cables. The cards are wired in an NVLink mesh, but one token needs about 150 tiny exchanges between them, and what counts is the delay per exchange, not the bandwidth. The generic path took 31–40 microseconds each. A measured NVLink route takes 6–8. That alone: 41 → 50 tok/s.

4️⃣ The model's own draft model. It proposes seven tokens, the big model checks them in one pass. On code, four to seven are accepted. 50 → 90–113 tok/s.

The part I find most useful is what did not work.

I was convinced that slicing every weight matrix across eight cards was wasteful, and that giving each card its own block of layers, moving only a small residual between them, had to be faster. So I built it. It moves far less data. It is also less than half as fast: 21 tok/s against 50.

The reason is simple once measured. Every token has to read about 265 MB of weights per layer. One card reads 700 GB/s. Split by layer, only one card reads at a time. Sliced, all eight read at once. The transitions were never the bottleneck; memory was.

What is not solved yet: taking in a prompt is slow, around 300 tokens per second on long inputs. A million-token context you cannot fill in reasonable time is only half a feature. That is next.

Everything is public: the paper with all measurements including the wrong turns, every benchmark script, and the patches.

👉 https://github.com/cronos3k/8xV100Inkling-2-Small

This builds on a lot of other people's work: vLLM and the 1Cat Volta build of it, Thinking Machines for the model, Unsloth for the 2-bit quantisation, llama.cpp as the reference, OpenCode as the interface. Thank you.

Old hardware is not finished. It just needs software written for what it actually is.

#LocalAI #OpenSource #LLM #GPU #MachineLearning #Inference
