#!/usr/bin/env python3
"""needle.py LINES PORT MODEL [MAX_TOKENS]

Long-context check, same method as the V4.1 box test (~/coder/longctx_test.py): three codes hidden at
3 %, 50 % and 97 % of a long ledger; the model must return all three. Thinking off, greedy.
About 23 tokens per line: 5000 lines is roughly 115K tokens.
"""
import json, random, sys, time, urllib.request
n = int(sys.argv[1]); port = sys.argv[2]; model = sys.argv[3]; max_tokens = int(sys.argv[4]) if len(sys.argv) > 4 else 120
rnd = random.Random(n)
towns = ["Aalen", "Bremen", "Coburg", "Dessau", "Emden", "Fulda", "Gera", "Husum", "Jena", "Kassel", "Lindau", "Marburg"]
goods = ["copper wire", "oak planks", "glass jars", "wool bales", "steel bolts", "clay tiles", "paper reels", "salt sacks"]
codes = {p: "%s-%06d" % (t, rnd.randrange(10**6)) for p, t in ((0.03, "ALPHA"), (0.50, "BRAVO"), (0.97, "CHARLIE"))}
at = {int(n * p): (p, c) for p, c in codes.items()}
lines = []
for i in range(n):
    if i in at:
        lines.append("Record %07d: SECRET ACCESS CODE %s is %s." % (i, at[i][1].split("-")[0], at[i][1]))
    else:
        lines.append("Record %07d: depot %s received %d units of %s, invoice %d." % (i, rnd.choice(towns), rnd.randrange(10, 9999), rnd.choice(goods), rnd.randrange(10**7)))
q = ("Below is a ledger. Three records contain a SECRET ACCESS CODE (ALPHA, BRAVO, CHARLIE).\n\n" + "\n".join(lines)
     + "\n\nList the three secret access codes exactly, one per line, in the form NAME-number.")
body = json.dumps({"model": model, "messages": [{"role": "user", "content": q}], "max_tokens": max_tokens, "temperature": 0,
                   "reasoning_effort": "none", "chat_template_kwargs": {"reasoning_effort": "none"}}).encode()
t = time.time()
try:
    r = json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:%s/v1/chat/completions" % port, body, {"content-type": "application/json"}), timeout=6 * 3600))
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read()[:600].decode("utf8", "replace")); sys.exit(1)
dt = time.time() - t
out = r["choices"][0]["message"].get("content") or ""
u = r["usage"]
print("lines %d  prompt_tokens %d  completion_tokens %d  seconds %.1f  (%.0f prompt tok/s)" % (n, u["prompt_tokens"], u["completion_tokens"], dt, u["prompt_tokens"] / dt))
print("expected:", " ".join(codes.values()))
print("reply   :", out.strip().replace("\n", " | "))
print("RESULT  :", "PASS" if all(c in out for c in codes.values()) else "FAIL")
