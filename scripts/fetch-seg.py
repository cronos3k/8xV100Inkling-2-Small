#!/usr/bin/env python3
"""fetch-seg.py REPO DEST PATTERN [PATTERN...]

Segmented download of large files from a public Hugging Face repository: the part of each file that is
still missing is cut into chunks, and many curl range streams fetch the chunks at once, each bound to
one uplink and written straight to its offset in the file (no part files).

Streams per uplink come from INK2_SEG_STREAMS, e.g. "enp184s0f1:16 enp97s0f3np3:2".
Resumable at chunk granularity through FILE.seg.json. A file that an ordinary single-stream download
left unfinished is continued from its current length. Verification (size, sha256) is done afterwards
with:  fetch.py REPO DEST PATTERN... --verify-only
Standard library only.
"""
import fnmatch, json, os, queue, subprocess, sys, threading, time, urllib.request

CHUNK = int(os.environ.get("INK2_SEG_CHUNK_MB", "1024")) << 20   # 1 GiB per chunk unless overridden
lock = threading.Lock()
done_bytes = 0

def log(*a):
    print(time.strftime("%F %T"), *a, flush=True)

def tree(repo):
    out, url = [], f"https://huggingface.co/api/models/{repo}/tree/main?recursive=true&limit=1000"
    while url:
        with urllib.request.urlopen(url, timeout=60) as r:
            out += json.load(r)
            link = r.headers.get("Link", "")
        url = link[link.find("<") + 1:link.find(">")] if 'rel="next"' in link else None
    return [f for f in out if f.get("type") == "file"]

def load_state(path, size):
    sp = path + ".seg.json"
    if os.path.exists(sp):
        st = json.load(open(sp))
        if st.get("size") == size:
            return st
    base = os.path.getsize(path) if os.path.exists(path) else 0
    st = {"size": size, "base": min(base, size), "chunk": CHUNK, "done": []}
    save_state(path, st)
    return st

def save_state(path, st):
    tmp = path + ".seg.json.tmp"
    with open(tmp, "w") as f:
        json.dump(st, f)
    os.replace(tmp, path + ".seg.json")

def fetch_chunk(url, path, start, end, ifc):
    want = end - start + 1
    curl = subprocess.Popen(["curl", "--interface", ifc, "-L", "-s", "-S", "--fail", "-r", "%d-%d" % (start, end),
                             "--connect-timeout", "30", "--speed-limit", "20000", "--speed-time", "60",
                             "-w", "%{stderr}%{size_download} %{http_code}\n", url],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    dd = subprocess.Popen(["dd", "of=" + path, "bs=4M", "iflag=fullblock", "oflag=seek_bytes", "seek=%d" % start,
                           "conv=notrunc", "status=none"], stdin=curl.stdout)
    curl.stdout.close()
    err = curl.stderr.read().decode("utf8", "replace").strip().splitlines()
    curl.wait(); dd.wait()
    last = err[-1].split() if err else []
    ok = curl.returncode == 0 and dd.returncode == 0 and len(last) == 2 and last[1] == "206" and int(last[0]) == want
    return ok, " | ".join(err[-2:])

def worker(ifc, q, states):
    global done_bytes
    while True:
        try:
            repo, f, dest, idx, start, end = q.get_nowait()
        except queue.Empty:
            return
        path = os.path.join(dest, f["path"])
        url = f"https://huggingface.co/{repo}/resolve/main/{f['path']}"
        for attempt in range(60):
            ok, msg = fetch_chunk(url, path, start, end, ifc)
            if ok:
                break
            log("   retry %d chunk %d of %s via %s: %s" % (attempt + 1, idx, f["path"], ifc, msg[:160]))
            time.sleep(10)
        with lock:
            if ok:
                st = states[path]; st["done"].append(idx); save_state(path, st)
                done_bytes += end - start + 1
            else:
                log("   GAVE UP chunk %d of %s" % (idx, f["path"]))

def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    repo, dest, pats = a[0], a[1], a[2:]
    streams = []
    for spec in os.environ.get("INK2_SEG_STREAMS", "enp184s0f1:16").split():
        ifc, n = spec.split(":")
        streams += [ifc] * int(n)
    files = [f for f in tree(repo) if any(fnmatch.fnmatch(f["path"], p) for p in pats)]
    q, states, todo = queue.Queue(), {}, 0
    for f in sorted(files, key=lambda f: -f["size"]):
        path = os.path.join(dest, f["path"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path + ".sha256ok"):
            continue
        st = load_state(path, f["size"]); states[path] = st
        n = 0
        for idx, start in enumerate(range(st["base"], f["size"], st["chunk"])):
            if idx in st["done"]:
                continue
            end = min(start + st["chunk"], f["size"]) - 1
            q.put((repo, f, dest, idx, start, end)); todo += end - start + 1; n += 1
        log("   %s: %.2f GB present, %d chunks to fetch" % (f["path"], st["base"] / 1e9, n))
    log("%s: %.1f GB to fetch over %d streams (%s)" % (repo, todo / 1e9, len(streams), os.environ.get("INK2_SEG_STREAMS", "default")))
    if not todo:
        return 0
    threads = [threading.Thread(target=worker, args=(ifc, q, states), daemon=True) for ifc in streams]
    for t in threads:
        t.start()
    t0, last = time.time(), 0
    while any(t.is_alive() for t in threads):
        time.sleep(60)
        with lock:
            d = done_bytes
        log("   %.1f of %.1f GB in finished chunks, %.0f MB/s over the last minute, %.0f MB/s average" %
            (d / 1e9, todo / 1e9, (d - last) / 60e6, d / (time.time() - t0) / 1e6))
        last = d
    left = sum(1 for p, st in states.items() if len(st["done"]) < len(range(st["base"], st["size"], st["chunk"])))
    log("%s: finished, %d file(s) incomplete" % (repo, left))
    return 1 if left else 0

if __name__ == "__main__":
    sys.exit(main())
