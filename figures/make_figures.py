#!/usr/bin/env python3
"""make_figures.py: the figures for the Volta Wonderland write-up. Every number is a measurement from PLAN.md."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img")
INK, ACC, MUTE, GRID, BG = "#14213d", "#e85d04", "#8d99ae", "#e5e5e5", "#ffffff"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": MUTE, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
                     "figure.facecolor": BG, "axes.facecolor": BG, "savefig.dpi": 200})

def title(fig, head, sub):
    fig.text(0.06, 0.94, head, fontsize=21, fontweight="bold", color=INK, va="top")
    fig.text(0.06, 0.865, sub, fontsize=12.5, color=MUTE, va="top")

def foot(fig, text):
    fig.text(0.06, 0.03, text, fontsize=10, color=MUTE)

# 1 speed ladder
fig = plt.figure(figsize=(10, 6.2)); ax = fig.add_axes([0.36, 0.14, 0.56, 0.62])
steps = [("llama.cpp, 8 cards", 15), ("Volta engine, first run", 7.5), ("+ CUDA graphs", 41), ("+ NVLink route for exchanges", 50), ("+ drafter (code)", 101.5)]
names = [s[0] for s in steps][::-1]; vals = [s[1] for s in steps][::-1]
cols = [ACC if "drafter" in n else (MUTE if "llama" in n else INK) for n in names]
ax.barh(names, vals, color=cols, height=0.62)
labels = {"+ drafter (code)": "90-113", "Volta engine, first run": "7-8"}
for n, v in zip(names, vals):
    ax.text(v + 1.5, n, labels.get(n, "%g" % v) + " tok/s", va="center", fontsize=13, color=INK, fontweight="bold")
ax.set_xlim(0, 135); ax.set_xticks([]); ax.spines["bottom"].set_visible(False); ax.tick_params(length=0)
title(fig, "From 15 to about 100 tokens per second", "Inkling-2-Small (594B parameters, 17B active), single stream, eight Tesla V100 from 2017")
foot(fig, "Measured on 12 fixed prompts, greedy decoding. Drafter figure is for code prompts; prose runs at 39-56 tok/s.")
fig.savefig(os.path.join(OUT, "01-speed-ladder.png")); plt.close(fig)

# 2 exchange latency
fig = plt.figure(figsize=(10, 6.2)); ax = fig.add_axes([0.1, 0.16, 0.84, 0.58])
sizes = ["9 KB", "18 KB", "37 KB", "74 KB", "147 KB"]; nccl = [30.7, 32.3, 38.3, 40.2, 39.8]; nv = [6.0, 7.2, 7.8, 9.7, 29.7]
x = range(len(sizes)); w = 0.38
ax.bar([i - w / 2 for i in x], nccl, w, color=MUTE, label="NCCL (generic)"); ax.bar([i + w / 2 for i in x], nv, w, color=ACC, label="measured NVLink route")
for i, (a, b) in enumerate(zip(nccl, nv)):
    ax.text(i - w / 2, a + 0.8, "%.0f" % a, ha="center", fontsize=11.5, color=INK); ax.text(i + w / 2, b + 0.8, "%.0f" % b, ha="center", fontsize=11.5, color=INK, fontweight="bold")
ax.set_xticks(list(x)); ax.set_xticklabels(sizes); ax.set_ylabel("microseconds per exchange"); ax.set_xlabel("message size")
ax.yaxis.grid(True, color=GRID); ax.set_axisbelow(True); ax.legend(frameon=False, loc="upper left", ncol=2, bbox_to_anchor=(0, 1.12))
title(fig, "A token is about 150 tiny exchanges", "What counts between the cards is the delay per exchange, not the 150 GB/s of bandwidth")
foot(fig, "Eight cards, fp16 all-reduce, median of the engine's own start-up measurement.")
fig.savefig(os.path.join(OUT, "02-exchange-latency.png")); plt.close(fig)

# 3 layouts
fig = plt.figure(figsize=(10, 6.2)); ax = fig.add_axes([0.1, 0.16, 0.84, 0.58])
lay = ["sliced\neight ways", "two boards\nof four", "one block of\nlayers per card"]; one = [50, 40, 21]; many = [145, 116, 65]; lab = ["4 parallel", "4 parallel", "8 parallel"]
x = range(3)
ax.bar([i - w / 2 for i in x], one, w, color=INK, label="one stream"); ax.bar([i + w / 2 for i in x], many, w, color=ACC, label="several streams, total")
for i in x:
    ax.text(i - w / 2, one[i] + 2, "%d" % one[i], ha="center", fontweight="bold", color=INK); ax.text(i + w / 2, many[i] + 2, "%d\n(%s)" % (many[i], lab[i]), ha="center", fontsize=11, color=INK)
ax.set_xticks(list(x)); ax.set_xticklabels(lay); ax.set_ylabel("tokens per second"); ax.set_ylim(0, 175)
ax.yaxis.grid(True, color=GRID); ax.set_axisbelow(True); ax.legend(frameon=False, loc="upper right")
title(fig, "Three ways to spread one model over eight cards", "Without drafter. Splitting by layer moves the least data and is still the slowest")
foot(fig, "Reason: each token reads about 265 MB of weights per layer; one card reads 700 GB/s; only slicing lets all eight read at once.")
fig.savefig(os.path.join(OUT, "03-layouts.png")); plt.close(fig)

# 4 topology
fig = plt.figure(figsize=(10, 6.2)); ax = fig.add_axes([0.05, 0.1, 0.9, 0.68]); ax.set_xlim(0, 10); ax.set_ylim(0, 5.2); ax.axis("off")
pos = {0: (1.2, 3.9), 1: (3.6, 3.9), 2: (1.2, 1.7), 3: (3.6, 1.7), 5: (6.4, 3.9), 4: (8.8, 3.9), 7: (6.4, 1.7), 6: (8.8, 1.7)}
double = [(0, 1), (0, 2), (2, 3), (1, 5), (3, 7), (4, 5), (4, 6), (6, 7)]; single = [(0, 3), (1, 2), (1, 3), (0, 4), (2, 6), (5, 6), (5, 7), (4, 7)]
from matplotlib.patches import FancyArrowPatch
for a, b in single:
    if (a, b) in ((0, 4), (2, 6)):
        rad = -0.22 if a == 0 else 0.22
        ax.add_patch(FancyArrowPatch(pos[a], pos[b], connectionstyle='arc3,rad=%s' % rad, arrowstyle='-', color=MUTE, lw=1.6, zorder=1))
        continue
    ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color=MUTE, lw=1.6, zorder=1)
for a, b in double:
    ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color=ACC, lw=4.2, zorder=2)
for k, (px, py) in pos.items():
    ax.add_patch(Circle((px, py), 0.42, color=INK, zorder=3)); ax.text(px, py, str(k), color="white", ha="center", va="center", fontsize=15, fontweight="bold", zorder=4)
ax.plot([0.6, 1.2], [0.1, 0.1], color=ACC, lw=4.2); ax.text(1.3, 0.1, "double link, 48 GB/s measured", va="center", fontsize=11.5, color=INK)
ax.plot([4.4, 5.0], [0.1, 0.1], color=MUTE, lw=1.6); ax.text(5.1, 0.1, "single link, 24 GB/s", va="center", fontsize=11.5, color=INK)
ax.text(7.5, 0.1, "no link: PCIe, 10 GB/s", va="center", fontsize=11.5, color=MUTE); ax.text(2.4, 2.8, "board A", ha="center", fontsize=11, color=MUTE); ax.text(7.6, 2.8, "board B", ha="center", fontsize=11, color=MUTE)
title(fig, "Eight cards, each wired to four of the other seven", "NVLink mesh of the V100 box: 48 links at 25.8 GB/s. The remaining pairs talk over PCIe")
fig.savefig(os.path.join(OUT, "04-nvlink-mesh.png")); plt.close(fig)

# 5 numbers card
fig = plt.figure(figsize=(10, 6.2)); ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); fig.patch.set_facecolor(INK)
ax.text(0.06, 0.88, "Welcome to Volta Wonderland", color="white", fontsize=27, fontweight="bold")
ax.text(0.06, 0.80, "A 594-billion-parameter open model on eight GPUs from 2017", color="#cbd5e1", fontsize=15)
cells = [("594B", "parameters in the model\n(17B active per token)"), ("8 x V100", "Tesla V100-SXM2, 32 GB\nreleased 2017"), ("90-113", "tokens per second on code\none stream, with drafter"),
         ("1,048,576", "token context window\n(retrieval tested to 56K so far)"), ("2-bit", "expert weights, coding bench\n13 of 16 tasks passed"), ("15", "tokens per second with\nllama.cpp on the same cards")]
for i, (big, small) in enumerate(cells):
    cx = 0.06 + (i % 3) * 0.31; cy = 0.52 if i < 3 else 0.2
    ax.text(cx, cy + 0.07, big, color=ACC, fontsize=30, fontweight="bold"); ax.text(cx, cy - 0.06, small, color="white", fontsize=12.5, linespacing=1.4)
ax.text(0.06, 0.05, "Open problem: prompt intake is still slow (about 300-1,300 tok/s). Details and all scripts in the repository.", color="#cbd5e1", fontsize=10.5)
fig.savefig(os.path.join(OUT, "00-title-card.png"), facecolor=INK); plt.close(fig)
print(sorted(os.listdir(OUT)))
