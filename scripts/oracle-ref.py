#!/usr/bin/env python3
"""oracle-ref.py OUTDIR [PORT] [MODEL]

Record the reference answers of an OpenAI-compatible server for a fixed prompt set:
greedy (temperature 0), thinking off, with the top-5 log-probabilities of every generated token.
The same script is later run against the engine port; compare-ref.py then lines the two up.
Standard library only.
"""
import json, os, sys, time, urllib.request

PROMPTS = [
    ("code_py", "Write a Python function `merge_intervals(intervals)` that merges overlapping closed intervals given as a list of [start, end] pairs and returns them sorted. Include a short docstring. Code only."),
    ("code_rust", "Write a Rust function `fn is_palindrome(s: &str) -> bool` that ignores case and every character that is not alphanumeric. Code only."),
    ("json", "Return a JSON object with the keys name, founded and cities for an invented shipping company. founded is a year as a number, cities is an array of exactly four port cities. JSON only, no explanation."),
    ("math", "A tank holds 2400 litres. Pump A fills it in 40 minutes, pump B empties it in 60 minutes. Both run from empty. After how many minutes is the tank full? Show the calculation in three lines."),
    ("logic", "Anna is taller than Ben. Ben is taller than Carla. Dora is shorter than Carla. Who is second tallest? Answer in one sentence."),
    ("prose_en", "Write one paragraph of about 120 words describing a harbour town at dawn, in plain modern English."),
    ("prose_de", "Schreibe einen Absatz von etwa 100 Woertern ueber eine Werkstatt, in der alte Rechenmaschinen repariert werden. Sachlich, ohne Aufzaehlungen."),
    ("legal", "Explain in four sentences the difference between a warranty claim and a guarantee under German sales law (Gewaehrleistung and Garantie)."),
    ("summary", "Summarise in two sentences: The company moved its servers from a rented data centre into its own basement. Power costs fell by a third, but the team now handles cooling, backups and hardware faults itself, which takes about one working day per week."),
    ("translate", "Translate into German: 'The replacement part arrived on Tuesday, but the invoice still lists the old serial number.'"),
    ("facts", "List the five largest moons of Saturn by diameter, largest first, one per line, names only."),
    ("refactor", "Rewrite this C function so that it cannot overflow the buffer, and say in one sentence what you changed:\n\nvoid greet(const char *name) {\n    char buf[16];\n    strcpy(buf, \"Hello, \");\n    strcat(buf, name);\n    puts(buf);\n}"),
]

def post(port, path, body, timeout=1800):
    req = urllib.request.Request("http://127.0.0.1:%s%s" % (port, path), json.dumps(body).encode(), {"content-type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))

def main():
    out = sys.argv[1]
    port = sys.argv[2] if len(sys.argv) > 2 else "18141"
    model = sys.argv[3] if len(sys.argv) > 3 else "inkling-2-small-iq2"
    os.makedirs(out, exist_ok=True)
    total_tok = total_s = 0.0
    for name, prompt in PROMPTS:
        body = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 320, "temperature": 0,
                "seed": 1, "logprobs": True, "top_logprobs": 5,
                "reasoning_effort": "none", "chat_template_kwargs": {"reasoning_effort": "none"}}
        t = time.time()
        try:
            r = post(port, "/v1/chat/completions", body)
        except urllib.error.HTTPError as e:
            print(name, "HTTP", e.code, e.read()[:400].decode("utf8", "replace")); continue
        dt = time.time() - t
        ch = r["choices"][0]
        text = ch["message"].get("content") or ""
        u = r.get("usage", {})
        n = u.get("completion_tokens", 0)
        total_tok += n; total_s += dt
        json.dump({"name": name, "prompt": prompt, "request": body, "response": r, "seconds": dt}, open(os.path.join(out, name + ".json"), "w"), indent=1)
        print("%-10s %4d prompt tok, %4d out tok, %6.1f s, %5.1f tok/s, finish %s" % (name, u.get("prompt_tokens", 0), n, dt, n / dt if dt else 0, ch.get("finish_reason")))
        print("   " + text.strip().replace("\n", "\n   ")[:1200])
    if total_s:
        print("TOTAL %d tokens in %.1f s = %.1f tok/s including prompt time" % (total_tok, total_s, total_tok / total_s))

if __name__ == "__main__":
    main()
