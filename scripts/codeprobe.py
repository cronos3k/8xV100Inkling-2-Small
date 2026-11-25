#!/usr/bin/env python3
"""codeprobe.py OUTDIR PORT MODEL [--think] [--only name,name] [--jobs N]

Coding probe for quantisation damage. Every task is sent greedy (temperature 0) to an OpenAI-compatible
server; the code in the answer is then compiled or executed against hidden tests in OUTDIR/<task>/.
The tasks aim at what low-bit weights lose first: exact recall of rare constants (SHA-256, CRC-32),
long coherent programs (a small Scheme), byte-exact copying, strict semantics (operator precedence,
overflow, expiry rules), and five languages (Python, C, C++, JavaScript, SQL).
Default is thinking off (the hardest setting: no self-correction). --think leaves the model's default effort.
"""
import concurrent.futures, json, os, random, re, subprocess, sys, time, urllib.request

A = [x for x in sys.argv[1:] if not x.startswith("--")]
OUT, PORT, MODEL = A[0], A[1], A[2]
THINK = "--think" in sys.argv
ONLY = next((sys.argv[i + 1].split(",") for i, x in enumerate(sys.argv) if x == "--only"), None)
JOBS = int(next((sys.argv[i + 1] for i, x in enumerate(sys.argv) if x == "--jobs"), "4"))
if ONLY:
    A = [x for x in A if x != ",".join(ONLY)]


def sh(cmd, cwd, timeout=60):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           env={"PATH": "/usr/bin:/bin", "HOME": cwd, "LANG": "C.UTF-8"})
        return p.returncode, (p.stdout + p.stderr)[-1500:]
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT after %d s" % timeout


def blocks(text):
    return [(m.group(1).lower(), m.group(2)) for m in re.finditer(r"```([A-Za-z0-9+#]*)[^\n]*\n(.*?)```", text, re.S)]


def code_of(text, langs):
    bs = blocks(text)
    pick = [c for l, c in bs if l in langs] or [c for l, c in bs]
    return max(pick, key=len) if pick else None


def py_task(test_src, forbid=None):
    def check(ans, d):
        code = code_of(ans, ("python", "py", "python3"))
        if code is None:
            return False, "no code block"
        if forbid and re.search(forbid, code):
            return False, "uses forbidden construct /%s/" % forbid
        open(os.path.join(d, "sol.py"), "w").write(code)
        open(os.path.join(d, "test.py"), "w").write("import sys\nsys.path.insert(0, '.')\n" + test_src + "\nprint('ALL-OK')\n")
        rc, out = sh(["python3", "-I", "test.py"], d)
        return rc == 0 and "ALL-OK" in out, out.strip()[-500:]
    return check


def c_task(pre, main, compiler, std, langs, ext):
    def check(ans, d):
        code = code_of(ans, langs)
        if code is None:
            return False, "no code block"
        src = "sol." + ext
        open(os.path.join(d, src), "w").write(pre + "\n" + code + "\n" + main)
        rc, out = sh([compiler, "-std=" + std, "-O1", "-g", "-Wall", "-Wextra", "-fsanitize=address,undefined",
                      "-fno-sanitize-recover=all", src, "-o", "sol.bin"], d, 120)
        warn = out.count("warning:")
        if rc != 0:
            return False, "COMPILE ERROR: " + out[-600:]
        rc, out = sh(["./sol.bin"], d)
        return rc == 0 and "ALL-OK" in out, ("%d warning(s); " % warn) + out.strip()[-500:]
    return check


T = []


def task(name, prompt, check):
    T.append((name, prompt, check))


# 1 --- strict semantics: precedence, associativity, error handling
task("expr_eval", """Write a Python function `evaluate(expr: str) -> float` that evaluates an arithmetic expression given as a string.
Supported: decimal numbers such as 3 or 2.5, the binary operators + - * / and ** , unary minus (which may be repeated), parentheses, and spaces anywhere between tokens.
Rules, identical to Python: * and / bind tighter than + and -; ** binds tighter than a unary minus on its left (so -2**2 is -4) and is right-associative (2**3**2 is 512); the right operand of ** may itself start with a unary minus (2**-1 is 0.5).
Raise ValueError for any malformed input, including the empty string.
Do not use eval, exec, compile or the ast module. Reply with one Python code block and nothing else.""",
     py_task(r'''
from sol import evaluate
for e in ["1+2*3", "-2**2", "2**3**2", "(1+2)*(3-4)/5", " 3.5 * -2 ", "--3", "2*-3", "10/4", "((2))", "2**-1", "-(3+4)*2", "8/2/2", "2-3-4", "1.5+0.5", "2**-2**2", "-(-(1))", "7 - -2"]:
    got, want = evaluate(e), eval(e)
    assert abs(got - want) < 1e-9, (e, got, want)
for e in ["1+", "(1", "2 3", "", "1+*2", "abc", "1)", "()", "2**", "1 + (2 * 3"]:
    try:
        evaluate(e)
    except ValueError:
        continue
    raise AssertionError("no ValueError for %r" % e)
''', forbid=r"(?<![\w.])eval\s*\(|(?<![\w.])exec\s*\(|import ast|(?<![\w.])compile\s*\("))

# 2 --- state machine with exact rules
task("ttl_cache", """Write a Python class `TTLCache` with this exact behaviour.
`TTLCache(capacity, ttl, clock=time.monotonic)`: `clock` is a zero-argument function returning the current time in seconds.
`put(key, value)`: store or overwrite; this sets the entry's timestamp to now and makes it the most recently used. When a NEW key is inserted and the cache already holds `capacity` entries, first drop every expired entry; only if it is still full, evict the least recently used entry.
`get(key)`: return the value, or None if the key is missing or expired (an expired entry is removed). A successful get makes the entry the most recently used but does NOT change its timestamp.
`len(cache)`: the number of entries that are not expired.
An entry is expired when clock() - timestamp >= ttl.
Reply with one Python code block and nothing else.""",
     py_task(r'''
from sol import TTLCache
t = [0.0]
c = TTLCache(2, 10, clock=lambda: t[0])
c.put("a", 1); t[0] = 1; c.put("b", 2)
assert c.get("a") == 1
c.put("c", 3)
assert c.get("b") is None and c.get("a") == 1 and c.get("c") == 3
assert len(c) == 2
t[0] = 10
assert c.get("a") is None
assert len(c) == 1
t[0] = 10.5; c.put("d", 4)
assert len(c) == 2
t[0] = 11
assert c.get("c") is None and len(c) == 1
c2 = TTLCache(2, 10, clock=lambda: t[0]); t[0] = 100; c2.put("x", 1); t[0] = 105
assert c2.get("x") == 1
t[0] = 110
assert c2.get("x") is None, "get must not refresh the timestamp"
t[0] = 200; c2.put("y", 1); t[0] = 205; c2.put("y", 2); t[0] = 212
assert c2.get("y") == 2, "overwrite must reset the timestamp"
c3 = TTLCache(2, 10, clock=lambda: t[0]); t[0] = 300; c3.put("old", 1); t[0] = 305; c3.put("live", 2); t[0] = 306
assert c3.get("old") == 1
t[0] = 311
c3.put("new", 3)
assert c3.get("live") == 2 and c3.get("new") == 3 and len(c3) == 2, "expired entries must be dropped before LRU eviction"
'''))

# 3 --- exact recall of rare constants
task("sha256", """Implement SHA-256 from scratch in Python: a function `sha256(data: bytes) -> str` returning the lowercase hex digest.
No imports at all. Reply with one Python code block and nothing else.""",
     py_task(r'''
import hashlib
from sol import sha256
for n in [0, 1, 3, 55, 56, 57, 63, 64, 65, 119, 120, 1000]:
    d = bytes((i * 37 + 11) % 256 for i in range(n))
    assert sha256(d) == hashlib.sha256(d).hexdigest(), "wrong digest for %d bytes" % n
assert sha256(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
''', forbid=r"hashlib|\bimport\b"))

# 4 --- C: bit-exact algorithm, overflow, in-place string work, under ASan/UBSan
task("c_utils", """Write these three C11 functions. Do not write main(). Assume <stdint.h>, <stddef.h>, <string.h>, <limits.h> and <ctype.h> are already included.
1. `uint32_t crc32_ieee(const uint8_t *data, size_t len)`: the standard CRC-32 (as in zlib and PNG), computed bit by bit without a lookup table.
2. `int parse_int32(const char *s, int32_t *out)`: strict decimal parser. Accepts an optional single '+' or '-' followed by one or more digits and nothing else (no spaces, no other characters). Returns 0 and stores the value on success. Returns -1 and leaves *out unchanged if the text is malformed or the value does not fit in int32_t. It must not rely on signed overflow.
3. `void reverse_words(char *s)`: reverses the order of the words in place, using no extra buffer. Words are separated by single spaces and there are no leading or trailing spaces. "the quick brown fox" becomes "fox brown quick the".
Reply with one C code block and nothing else.""",
     c_task("#include <stdint.h>\n#include <stddef.h>\n#include <string.h>\n#include <limits.h>\n#include <ctype.h>\n#include <stdio.h>\n#include <stdlib.h>\n", r'''
#define CHECK(c) do { if (!(c)) { printf("FAILED line %d: %s\n", __LINE__, #c); return 1; } } while (0)
int main(void) {
    int32_t v = 77;
    CHECK(crc32_ieee((const uint8_t *)"123456789", 9) == 0xCBF43926u);
    CHECK(crc32_ieee((const uint8_t *)"", 0) == 0u);
    CHECK(crc32_ieee((const uint8_t *)"a", 1) == 0xE8B7BE43u);
    CHECK(parse_int32("2147483647", &v) == 0 && v == 2147483647);
    CHECK(parse_int32("-2147483648", &v) == 0 && v == INT32_MIN);
    CHECK(parse_int32("+7", &v) == 0 && v == 7);
    CHECK(parse_int32("-0", &v) == 0 && v == 0);
    CHECK(parse_int32("0000123", &v) == 0 && v == 123);
    v = 77;
    CHECK(parse_int32("2147483648", &v) == -1 && v == 77);
    CHECK(parse_int32("-2147483649", &v) == -1 && v == 77);
    CHECK(parse_int32("99999999999999999999", &v) == -1 && v == 77);
    CHECK(parse_int32("", &v) == -1 && v == 77);
    CHECK(parse_int32("+", &v) == -1 && v == 77);
    CHECK(parse_int32("-", &v) == -1);
    CHECK(parse_int32("12a", &v) == -1 && v == 77);
    CHECK(parse_int32(" 7", &v) == -1);
    CHECK(parse_int32("7 ", &v) == -1);
    CHECK(parse_int32("+-7", &v) == -1);
    char a[] = "the quick brown fox"; reverse_words(a); CHECK(strcmp(a, "fox brown quick the") == 0);
    char b[] = "a"; reverse_words(b); CHECK(strcmp(b, "a") == 0);
    char c[] = ""; reverse_words(c); CHECK(strcmp(c, "") == 0);
    char d[] = "ab cde"; reverse_words(d); CHECK(strcmp(d, "cde ab") == 0);
    puts("ALL-OK");
    return 0;
}
''', "gcc", "c11", ("c", "h"), "c"))


# 5 --- SQL window functions
def sql_check(ans, d):
    q = code_of(ans, ("sql", "sqlite"))
    if q is None:
        return False, "no code block"
    open(os.path.join(d, "query.sql"), "w").write(q)
    import sqlite3
    rows = [(1, "ann", 40, "2024-01-01"), (2, "bob", 100, "2024-01-01"), (3, "ann", 30, "2024-01-02"), (4, "ann", 30, "2024-01-02"),
            (5, "cy", 99, "2024-01-03"), (6, "ann", 500, "2024-01-05"), (7, "dee", 60, "2024-01-02"), (8, "dee", 39, "2024-01-04"),
            (9, "dee", 1, "2024-01-04"), (10, "bob", 5, "2024-01-09"), (11, "eve", 50, "2024-01-03"), (12, "eve", 50, "2024-01-01")]
    want, tot = {}, {}
    for i, c, a, day in sorted(rows, key=lambda r: (r[3], r[0])):
        tot[c] = tot.get(c, 0) + a
        if tot[c] >= 100 and c not in want:
            want[c] = day
    want = sorted(want.items())
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT, amount INTEGER, day TEXT)")
    db.executemany("INSERT INTO orders VALUES (?,?,?,?)", rows)
    try:
        got = [tuple(r) for r in db.execute(q.strip().rstrip(";"))]
    except Exception as e:
        return False, "SQL error: %s" % e
    return got == want, "got %s want %s" % (got, want)


task("sql_window", """SQLite. Table `orders(id INTEGER PRIMARY KEY, customer TEXT, amount INTEGER, day TEXT)`, where day is an ISO date.
Write ONE SELECT statement that returns, for each customer, the day on which the customer's running total of amount (orders taken in order of day, then id) first reached or exceeded 100. Columns: customer, day. Customers whose total never reaches 100 are left out. Order by customer.
Reply with one SQL code block and nothing else.""", sql_check)

# 6 --- regex precision
task("regex_ipv4", """In Python, assign to a variable named PATTERN a raw-string regular expression that, used with re.fullmatch, accepts exactly the valid dotted-quad IPv4 addresses: four decimal numbers 0 to 255 separated by dots, with no leading zeros (the number zero is written as 0).
Reply with one Python code block and nothing else.""",
     py_task(r'''
import re
from sol import PATTERN
for s in ["0.0.0.0", "255.255.255.255", "192.168.1.1", "1.2.3.4", "10.0.0.255", "249.250.199.100", "9.99.100.200"]:
    assert re.fullmatch(PATTERN, s), "rejects " + s
for s in ["256.1.1.1", "1.1.1", "1.1.1.1.1", "01.1.1.1", "1.1.1.1 ", "a.b.c.d", "1..1.1", "300.1.1.1", "1.1.1.-1", "", "00.0.0.0", "1.1.1.1\n", "1.1.1.260", "1,1,1,1", "1.1.1.1.", "999.1.1.1", "1.1.1.025"]:
    assert not re.fullmatch(PATTERN, s), "accepts %r" % s
'''))

# 7 --- executing code in the head
SNIPPET = r'''def make():
    fs = []
    for i in range(3):
        fs.append(lambda x, i=i: x + i)
    gs = [lambda x: x * j for j in range(3)]
    return fs, gs

fs, gs = make()
a = [f(10) for f in fs]
b = [g(10) for g in gs]

def app(x, acc=[]):
    acc.append(x)
    return acc

c = app(1); d = app(2)
print(a, b, c is d, len(d))
print(7 // -2, -7 % 3, round(2.5), round(3.5), 0.1 + 0.2 == 0.3)
s = "abcdef"
print(s[::-2], s[-2:1:-1], sorted({3: 'a', 1: 'b'}), [*map(lambda p: p[0] * p[1], zip("ab", (2, 1)))])
'''


def trace_check(ans, d):
    open(os.path.join(d, "snippet.py"), "w").write(SNIPPET)
    rc, want = sh(["python3", "-I", "snippet.py"], d)
    got = code_of(ans, ("", "text", "python", "output", "plaintext", "txt"))
    if got is None:
        got = ans
    g = [l.strip() for l in got.strip().splitlines() if l.strip()]
    w = [l.strip() for l in want.strip().splitlines()]
    return g == w, "got %s want %s" % (g, w)


task("trace", "What does this Python 3 program print? Reply with exactly the three printed lines in one code block and nothing else.\n\n```python\n" + SNIPPET + "```", trace_check)

# 8 --- finding several bugs at once
task("bugfix", """This module has several bugs. Intended behaviour:
`lower_bound(a, x)`: a is sorted ascending; return the first index i with a[i] >= x, or len(a) if there is none.
`merge_k(lists)`: each inner list is sorted ascending; return one merged sorted list. Inner lists may be empty, and the function must not modify its arguments.

```python
import heapq

def lower_bound(a, x):
    lo, hi = 0, len(a) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < x:
            lo = mid
        else:
            hi = mid
    return lo

def merge_k(lists):
    heap = [(lst[0], lst) for lst in lists]
    heapq.heapify(heap)
    out = []
    while heap:
        val, lst = heapq.heappop(heap)
        out.append(val)
        lst.pop(0)
        if lst:
            heapq.heappush(heap, (lst[0], lst))
    return out
```
Reply with the corrected module in one Python code block and nothing else.""",
     py_task(r'''
import bisect, copy
from sol import lower_bound, merge_k
for a in [[], [1], [1, 2, 2, 3, 5], [2, 2, 2], [1, 3, 5, 7, 9, 11]]:
    for x in range(-1, 13):
        assert lower_bound(a, x) == bisect.bisect_left(a, x), (a, x, lower_bound(a, x))
for ls in [[[1, 4, 7], [], [2, 2, 9], [3]], [], [[], []], [[5]], [[1, 1], [1, 1], [0]], [[3, 4], [1, 2], [2, 3]]]:
    keep = copy.deepcopy(ls)
    assert merge_k(ls) == sorted(v for l in keep for v in l), ls
    assert ls == keep, "arguments were modified"
'''))

# 9 --- a long coherent program
task("mini_scheme", """Write a Python module with a function `run(src: str) -> list` that interprets a small Scheme dialect. `run` evaluates every top-level form in order and returns the list of the values of all forms that are not `define`.
Language: integer literals (possibly negative, such as -3); symbols; `(define name expr)` and `(define (name params...) body)`; `(lambda (params...) body)` with lexical scoping and closures; `(if cond then else)`; `(let ((name expr) ...) body)`; function application.
Built-ins: `+` and `*` with any number of arguments; `-` with one argument (negation) or two; `<` and `=` with two arguments, returning Python True or False. In `if`, only False counts as false.
Recursion must work. Reply with one Python code block and nothing else.""",
     py_task(r'''
from sol import run
assert run("(+ 1 2)") == [3]
assert run("(define x 5) (* x x)") == [25]
assert run("(define (fact n) (if (< n 2) 1 (* n (fact (- n 1))))) (fact 10)") == [3628800]
assert run("(define fib (lambda (n) (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2)))))) (fib 15)") == [610]
assert run("(define (make-adder n) (lambda (x) (+ x n))) (define add5 (make-adder 5)) (add5 10) ((make-adder 1) 1)") == [15, 2]
assert run("(let ((x 2) (y 3)) (* x y))") == [6]
assert run("(define x 1) (define (f) x) (let ((x 99)) (f))") == [1], "scoping must be lexical"
assert run("(if (= 1 1) 10 20) (if (< 2 1) 10 20) (if 0 1 2)") == [10, 20, 1]
assert run("(- 5) (- 10 3) (+ 1 2 3 4) (+ -3 5) (* 2 3 4)") == [-5, 7, 10, 2, 24]
assert run("((lambda (f x) (f (f x))) (lambda (y) (* y y)) 3)") == [81]
assert run("(define (count n acc) (if (= n 0) acc (count (- n 1) (+ acc 1)))) (count 150 0)") == [150]
assert run("(define (compose f g) (lambda (x) (f (g x))))\n(define inc (lambda (x) (+ x 1)))\n(define dbl (lambda (x) (* x 2)))\n((compose inc dbl) 5) ((compose dbl inc) 5)") == [11, 12]
assert run("(< 1 2)") == [True]
'''))


# 10 --- byte-exact copying with three edits
def make_cfg():
    r = random.Random(4217)

    def hx(n):
        return "".join(r.choice("0123456789abcdef") for _ in range(n))
    lines = ["# deployment manifest", "version: 7", "services:"]
    for name, port in (("gateway", 8443), ("worker", 9100), ("billing", 7001), ("search", 9200), ("mailer", 2525)):
        lines += ["  %s:" % name, "    image: registry.internal/%s@sha256:%s" % (name, hx(64)), "    port: %d" % port,
                  "    token: %s-%s-%s-%s-%s" % (hx(8), hx(4), hx(4), hx(4), hx(12)), "    timeout: %d" % r.randrange(5, 90),
                  "    debug: %s" % r.choice(("true", "false")), "    checksum: %s" % hx(40)]
    return lines


def cfg_check(ans, d):
    src = make_cfg()
    want = []
    sec = None
    for l in src:
        if l.startswith("  ") and not l.startswith("    "):
            sec = l.strip().rstrip(":")
        if sec == "gateway" and l.strip().startswith("port:"):
            l = "    port: 9443"
        if sec == "worker" and l.strip().startswith("debug:"):
            continue
        want.append(l)
        if sec == "billing" and l.strip().startswith("timeout:"):
            want.append("    retries: 5")
    got = code_of(ans, ("yaml", "yml", ""))
    if got is None:
        return False, "no code block"
    g = [l.rstrip() for l in got.rstrip().splitlines()]
    open(os.path.join(d, "got.yaml"), "w").write("\n".join(g))
    open(os.path.join(d, "want.yaml"), "w").write("\n".join(want))
    if g == want:
        return True, "identical, %d lines" % len(g)
    diff = [(i + 1, a, b) for i, (a, b) in enumerate(zip(g, want)) if a != b]
    return False, "%d vs %d lines; first differences: %s" % (len(g), len(want), diff[:3])


task("exact_copy", "Here is a YAML file. Output the complete file again with exactly these three changes and no others; every other character must stay identical.\n1. In service gateway, change the port to 9443.\n2. In service worker, delete the debug line.\n3. In service billing, add a line `retries: 5` directly after the timeout line, with the same indentation.\nReply with one YAML code block and nothing else.\n\n```yaml\n" + "\n".join(make_cfg()) + "\n```", cfg_check)

# 11 --- concurrency
task("asyncio_limit", """Write `async def gather_limited(fns, limit)` in Python. `fns` is a list of zero-argument callables, each returning an awaitable. Run them with at most `limit` running at the same time, starting them in list order, and return the list of results in the order of `fns`. If any of them raises, cancel everything that is still running, start nothing further, and re-raise that exception to the caller. An empty list returns [].
Reply with one Python code block and nothing else.""",
     py_task(r'''
import asyncio
from sol import gather_limited
async def main():
    running = 0; peak = 0; started = 0
    def mk(i, fail=False):
        async def f():
            nonlocal running, peak, started
            started += 1; running += 1; peak = max(peak, running)
            try:
                await asyncio.sleep(0.01 * (1 + (i * 7) % 3))
                if fail:
                    raise ValueError("boom")
                return i * i
            finally:
                running -= 1
        return f
    r = await gather_limited([mk(i) for i in range(12)], 3)
    assert r == [i * i for i in range(12)], r
    assert peak == 3, "peak concurrency %d" % peak
    assert await gather_limited([], 2) == []
    started = 0
    try:
        await gather_limited([mk(i, fail=(i == 1)) for i in range(20)], 2)
        raise SystemExit("no exception was raised")
    except ValueError:
        pass
    s = started
    await asyncio.sleep(0.2)
    assert started == s and s < 20, "tasks started after the failure: %d then %d" % (s, started)
    assert running == 0, "%d task(s) left running" % running
asyncio.run(asyncio.wait_for(main(), 20))
'''))

# 12 --- C++: iterator handling, checked against brute force
task("cpp_intervals", """Write a C++17 class `IntervalSet` holding a set of integers as disjoint half-open intervals [lo, hi).
`void add(int lo, int hi)`: insert all integers in [lo, hi). `void remove(int lo, int hi)`: erase all integers in [lo, hi). Both do nothing when lo >= hi.
`bool contains(int x) const`.
`std::vector<std::pair<int,int>> intervals() const`: the intervals in ascending order, disjoint, and maximal (touching intervals such as [1,3) and [3,5) are merged into [1,5)).
Use std::map internally. Include the headers you need, do not write main(). Reply with one C++ code block and nothing else.""",
     c_task("#include <bitset>\n#include <cstdio>\n#include <cstdint>\n#include <vector>\n#include <utility>\n#include <algorithm>\n", r'''
int main() {
    IntervalSet s; std::bitset<300> b; uint32_t x = 12345;
    auto rnd = [&]() { x = x * 1664525u + 1013904223u; return (int)((x >> 16) % 300); };
    for (int it = 0; it < 6000; ++it) {
        int lo = rnd(), hi = std::min(300, lo + rnd() % 14); bool add = (rnd() % 5) < 3;
        if (it % 97 == 0) { lo = rnd(); hi = lo - 3; }
        if (add) { s.add(lo, hi); for (int i = lo; i < hi; ++i) b[i] = 1; }
        else { s.remove(lo, hi); for (int i = lo; i < hi; ++i) b[i] = 0; }
        std::vector<std::pair<int,int>> want;
        for (int i = 0; i < 300;) { if (b[i]) { int j = i; while (j < 300 && b[j]) ++j; want.push_back({i, j}); i = j; } else ++i; }
        if (s.intervals() != want) { std::printf("MISMATCH after operation %d\n", it); return 1; }
        int q = rnd();
        if (s.contains(q) != (bool)b[q]) { std::printf("contains() wrong after operation %d\n", it); return 1; }
    }
    std::puts("ALL-OK");
    return 0;
}
''', "g++", "c++17", ("cpp", "c++", "cc", "cxx"), "cpp"))


# 13 --- reading code: five planted defects
def ub_check(ans, d):
    a = ans.lower()
    found = {
        "pointer to local buffer": bool(re.search(r"local|dangling|stack|automatic|out of scope|goes out|lifetime", a)),
        "signed overflow is undefined": bool(re.search(r"undefined behaviou?r|signed.{0,40}overflow|overflow.{0,40}undefined", a)),
        "sizeof on a pointer parameter": bool(re.search(r"sizeof.{0,200}(pointer|decay)|(pointer|decay).{0,200}sizeof", a, re.S)),
        "malloc one byte short": bool(re.search(r"strlen\(s\)\s*\+\s*1|off.by.one|one byte|terminat", a)),
        "unsigned char never equals EOF": bool(re.search(r"eof", a) and re.search(r"unsigned char|\bint c\b|never|infinite", a)),
    }
    miss = [k for k, v in found.items() if not v]
    return not miss, "found %d of 5%s" % (5 - len(miss), "; missed: " + ", ".join(miss) if miss else "")


task("c_review", """List every bug in this C file, one numbered item per bug, each with a one-sentence explanation. Be complete but do not invent problems.

```c
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

char *read_name(void) {
    char buf[32];
    fgets(buf, sizeof(buf), stdin);
    return buf;
}

int sum_ok(int a, int b) {
    if (a + b < a) return 0;   /* overflow check */
    return 1;
}

void fill(int arr[], int v) {
    for (size_t i = 0; i < sizeof(arr) / sizeof(arr[0]); i++) arr[i] = v;
}

char *dup_upper(const char *s) {
    char *r = malloc(strlen(s));
    for (size_t i = 0; i <= strlen(s); i++) r[i] = s[i] & ~0x20;
    return r;
}

int main(void) {
    unsigned char c;
    while ((c = getchar()) != EOF) putchar(c);
    return 0;
}
```""", ub_check)

# 14 --- graph algorithm with error cases
task("topo_stages", """Write a Python function `schedule(tasks: dict[str, list[str]]) -> list[list[str]]`. Each key is a task and its value the list of tasks it depends on. Return the stages of a parallel build: stage 0 holds every task without dependencies, each later stage holds the tasks whose dependencies are all in earlier stages, every task is placed in the earliest possible stage, and each stage is sorted alphabetically. Raise ValueError if a dependency is not a key of the dict or if there is a cycle (a task depending on itself included). An empty dict returns [].
Reply with one Python code block and nothing else.""",
     py_task(r'''
from sol import schedule
assert schedule({"a": [], "b": ["a"], "c": ["a"], "d": ["b", "c"], "e": []}) == [["a", "e"], ["b", "c"], ["d"]]
assert schedule({}) == []
assert schedule({"z": [], "y": ["z"], "x": ["y"], "w": ["z"]}) == [["z"], ["w", "y"], ["x"]]
assert schedule({"a": [], "b": ["a"], "c": ["a", "b"]}) == [["a"], ["b"], ["c"]]
for bad in [{"a": ["b"], "b": ["a"]}, {"a": ["zzz"]}, {"a": ["a"]}, {"a": [], "b": ["c"], "c": ["d"], "d": ["b"]}]:
    try:
        schedule(bad)
    except ValueError:
        continue
    raise AssertionError("no ValueError for %r" % bad)
'''))


# 15 --- JavaScript
def js_check(ans, d):
    code = code_of(ans, ("javascript", "js", "node"))
    if code is None:
        return False, "no code block"
    test = r'''
const assert = require("assert");
const t = (a, b, want) => assert.strictEqual(deepEqual(a, b), want, JSON.stringify([String(a), String(b), want]));
t(1, 1, true); t(1, "1", false); t(NaN, NaN, true); t(0, -0, true); t(null, undefined, false); t(null, null, true);
t([1, [2, 3]], [1, [2, 3]], true); t([1, 2], [1, 2, 3], false); t([1, 2], {0: 1, 1: 2, length: 2}, false);
t({a: 1, b: {c: [1, 2]}}, {b: {c: [1, 2]}, a: 1}, true); t({a: 1}, {a: 1, b: undefined}, false); t({a: undefined}, {b: undefined}, false);
t(new Date(5), new Date(5), true); t(new Date(5), new Date(6), false); t(new Date(5), {}, false);
t(new Map([[1, {a: 1}]]), new Map([[1, {a: 1}]]), true); t(new Map([[1, 2]]), new Map([[1, 3]]), false);
t(new Set([1, 2]), new Set([2, 1]), true); t(new Set([1, 2]), new Set([1, 3]), false);
const a = {n: 1}; a.self = a; const b = {n: 1}; b.self = b; t(a, b, true);
const c = {n: 2}; c.self = c; t(a, c, false);
t([], {}, false); t("x", new String("x"), false);
console.log("ALL-OK");
'''
    open(os.path.join(d, "sol.js"), "w").write(code + "\n" + test)
    rc, out = sh(["node", "sol.js"], d)
    return rc == 0 and "ALL-OK" in out, out.strip()[-400:]


task("js_deep_equal", """Write a JavaScript function `deepEqual(a, b)` for Node.js, as a plain function declaration (no exports).
Rules: primitives compare with ===, except that NaN equals NaN. Arrays are equal when they have the same length and deep-equal elements; an array never equals a non-array. Plain objects are equal when they have the same set of own enumerable string keys and deep-equal values (a key holding undefined is different from a missing key). Two Date objects are equal when their time values are equal. Two Map objects are equal when they have the same keys (compared with ===) and deep-equal values. Two Set objects of primitives are equal when they contain the same values. Objects of different kinds are never equal, and a primitive never equals an object. Cyclic structures must not cause infinite recursion: two structures with the same shape of cycles are equal.
Reply with one JavaScript code block and nothing else.""", js_check)


# 16 --- hard and long: B-tree with deletion, invariants checked after random operations
task("btree", """Write a Python class `BTree` implementing a B-tree of minimum degree t as defined in CLRS.
`BTree(t)` with t >= 2; `insert(key)` (a key already present is ignored); `delete(key)` (does nothing if the key is absent); `key in tree`; `keys()` returning all keys as a sorted list.
The tree must expose `self.root`, and every node must have the attributes `keys` (the node's keys in ascending order) and `children` (the list of child nodes, empty for a leaf).
Invariants that must hold after every operation: every node except the root holds between t-1 and 2t-1 keys; the root holds at most 2t-1 keys, and at least one key if it has children; an internal node with k keys has exactly k+1 children; all leaves are at the same depth.
Reply with one Python code block and nothing else.""",
     py_task(r'''
import random
from sol import BTree
def check(tree, t):
    depths = set()
    def walk(n, lo, hi, d, is_root):
        ks = list(n.keys)
        assert ks == sorted(ks) and len(set(ks)) == len(ks), "keys of a node not sorted"
        assert len(ks) <= 2 * t - 1, "node too full"
        if not is_root:
            assert len(ks) >= t - 1, "node too empty"
        for k in ks:
            assert (lo is None or k > lo) and (hi is None or k < hi), "key outside the range of its subtree"
        if n.children:
            assert len(ks) >= 1, "internal node without keys"
            assert len(n.children) == len(ks) + 1, "wrong number of children"
            bounds = [lo] + ks + [hi]
            for i, c in enumerate(n.children):
                walk(c, bounds[i], bounds[i + 1], d + 1, False)
        else:
            depths.add(d)
    if tree.root is not None:
        walk(tree.root, None, None, 0, True)
    assert len(depths) <= 1, "leaves at different depths"
for t in (2, 3, 5):
    r = random.Random(t); tr = BTree(t); ref = set()
    for step in range(4000):
        k = r.randrange(400)
        if r.random() < 0.55:
            tr.insert(k); ref.add(k)
        else:
            tr.delete(k); ref.discard(k)
        if step % 5 == 0 or step > 3900:
            check(tr, t)
            assert tr.keys() == sorted(ref), "content differs at step %d (t=%d)" % (step, t)
        q = r.randrange(400)
        assert (q in tr) == (q in ref), "membership wrong at step %d" % step
    for k in sorted(ref):
        tr.delete(k); check(tr, t)
    assert tr.keys() == []
'''))


def ask(name, prompt):
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 12000 if THINK else 5000,
            "temperature": 0, "seed": 1}
    if not THINK:
        body.update({"reasoning_effort": "none", "chat_template_kwargs": {"reasoning_effort": "none"}})
    t = time.time()
    req = urllib.request.Request("http://127.0.0.1:%s/v1/chat/completions" % PORT, json.dumps(body).encode(),
                                 {"content-type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=3600))
    except urllib.error.HTTPError as e:
        return None, "HTTP %d %s" % (e.code, e.read()[:300]), 0, time.time() - t, ""
    m = r["choices"][0]["message"]
    return (m.get("content") or "", r["choices"][0].get("finish_reason"), r["usage"]["completion_tokens"], time.time() - t,
            m.get("reasoning_content") or "")


def one(t):
    name, prompt, check = t
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "prompt.txt"), "w").write(prompt)
    ans, fin, ntok, dt, think = ask(name, prompt)
    if ans is None:
        return name, False, fin, 0, dt
    open(os.path.join(d, "answer.md"), "w").write(ans)
    if think:
        open(os.path.join(d, "thinking.md"), "w").write(think)
    try:
        ok, detail = check(ans, d)
    except Exception as e:
        ok, detail = False, "checker error: %r" % e
    if fin != "stop":
        detail = "finish=%s; " % fin + detail
    json.dump({"ok": ok, "detail": detail, "tokens": ntok, "seconds": dt}, open(os.path.join(d, "result.json"), "w"))
    return name, ok, detail, ntok, dt


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    todo = [t for t in T if not ONLY or t[0] in ONLY]
    t0 = time.time()
    res = []
    with concurrent.futures.ThreadPoolExecutor(JOBS) as ex:
        for name, ok, detail, ntok, dt in ex.map(one, todo):
            res.append(ok)
            print("%-14s %s  %5d tok %6.1f s  %s" % (name, "PASS" if ok else "FAIL", ntok, dt, " ".join(str(detail).split())[:230]), flush=True)
    print("RESULT %d of %d passed, thinking %s, %.0f s wall" % (sum(res), len(res), "on" if THINK else "off", time.time() - t0))
