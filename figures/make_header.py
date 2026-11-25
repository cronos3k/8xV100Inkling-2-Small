#!/usr/bin/env python3
"""make_header.py: LinkedIn header, the server front photo with title and headline numbers."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
here = os.path.dirname(os.path.abspath(__file__))
W, H = 2400, 1256
NAVY, ACC, WHITE, SOFT = (13, 22, 43), (255, 106, 19), (255, 255, 255), (203, 213, 225)
F = "C:/Windows/Fonts/"
def font(name, size):
    return ImageFont.truetype(F + name, size)
photo = Image.open(os.path.join(here, "img", "server-front.jpg")).convert("RGB")
s = W / photo.width
photo = photo.resize((W, round(photo.height * s)), Image.LANCZOS)
photo = ImageEnhance.Contrast(photo).enhance(1.12); photo = ImageEnhance.Color(photo).enhance(1.18)
TOP = H - photo.height                      # photo sits at the bottom, title band above it
img = Image.new("RGBA", (W, H), NAVY + (255,)); img.paste(photo, (0, TOP))
veil = Image.new("RGBA", (W, H), (0, 0, 0, 0)); px = veil.load()
for y in range(H):
    if y < 470:
        a = 1.0
    elif y < 640:
        a = 1.0 - 0.9 * ((y - 470) / 170) ** 1.3      # fade from the title band into the photo
    elif y < 960:
        a = 0.10
    else:
        a = 0.10 + 0.86 * min(1.0, (y - 960) / 90) ** 0.9
    for x in range(W):
        px[x, y] = (NAVY[0], NAVY[1], NAVY[2], int(255 * a))
img = Image.alpha_composite(img, veil)
d = ImageDraw.Draw(img)
def shadowed(xy, text, f, fill):
    x, y = xy
    d.text((x + 4, y + 5), text, font=f, fill=(0, 0, 0, 170)); d.text(xy, text, font=f, fill=fill)
M = 110
d.rectangle([M, 70, M + 150, 84], fill=ACC)
shadowed((M, 100), "Welcome to", font("segoeuib.ttf", 84), SOFT)
shadowed((M - 6, 176), "Volta Wonderland", font("seguibl.ttf", 200), WHITE)
f2 = font("segoeuib.ttf", 70); t1 = "A 594-billion-parameter open model "
shadowed((M, 410), t1, f2, WHITE); shadowed((M + d.textlength(t1, font=f2), 410), "on eight GPUs from 2017", f2, ACC)
# number strip
cells = [("90-113", "tokens per second", "on code, one stream"), ("1,048,576", "token context", "window"), ("8 x V100", "32 GB each,", "inside this machine"), ("15", "tokens per second", "with llama.cpp")]
cw = (W - 2 * M) // len(cells); base = 1000
for i, (big, a, b) in enumerate(cells):
    x = M + i * cw
    if i:
        d.rectangle([x - 34, base + 20, x - 31, base + 215], fill=(255, 255, 255, 70))
    col = SOFT if i == 3 else ACC
    shadowed((x, base), big, font("seguibl.ttf", 104 if len(big) < 9 else 88), col)
    d.text((x + 4, base + 132), a, font=font("segoeui.ttf", 40), fill=WHITE); d.text((x + 4, base + 178), b, font=font("segoeui.ttf", 40), fill=WHITE)
out = os.path.join(here, "img", "00-header-server.png")
img.convert("RGB").save(out, quality=95); img.convert("RGB").resize((1200, 628), Image.LANCZOS).save(os.path.join(here, "img", "00-header-server-1200.png"))
print(out)
