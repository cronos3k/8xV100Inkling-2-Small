#!/usr/bin/env python3
"""fetch.py REPO DEST PATTERN [PATTERN...]   (options: --jobs N, --verify-only)

Download the files of a public Hugging Face model repository that match the patterns into DEST,
keeping the repository's folder layout. Resumable: run it again and it continues.
Each file is fetched with curl bound to the first working interface in INK2_DL_IFACES and then
checked against the size and the sha256 the Hub publishes. Standard library only.
"""
import fnmatch, hashlib, json, os, subprocess, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

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

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(16 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def verify(f, dest):
    p = os.path.join(dest, f["path"])
    if not os.path.exists(p):
        return "missing"
    if os.path.getsize(p) != f["size"]:
        return "size %d of %d" % (os.path.getsize(p), f["size"])
    oid = (f.get("lfs") or {}).get("oid")
    if oid:
        mark = p + ".sha256ok"
        if os.path.exists(mark) and open(mark).read().strip() == oid:
            return "ok"
        if sha256(p) != oid:
            return "sha256 mismatch"
        with open(mark, "w") as m:
            m.write(oid + "\n")
    return "ok"

def get(repo, f, dest, ifaces):
    p = os.path.join(dest, f["path"])
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.exists(p) and os.path.getsize(p) == f["size"]:
        return verify(f, dest)
    url = f"https://huggingface.co/{repo}/resolve/main/{f['path']}"
    for attempt in range(40):
        ifc = ifaces[attempt % len(ifaces)] if attempt >= 3 else ifaces[0]
        cmd = ["curl", "--interface", ifc, "-L", "-s", "-S", "-C", "-", "--connect-timeout", "30",
               "--speed-limit", "20000", "--speed-time", "120", "-o", p, url]
        rc = subprocess.call(cmd)
        have = os.path.getsize(p) if os.path.exists(p) else 0
        if have == f["size"]:
            return verify(f, dest)
        if have > f["size"]:
            return "larger than published (%d of %d)" % (have, f["size"])
        log("   retry %d %s via %s (curl rc %d, %.1f of %.1f GB)" % (attempt + 1, f["path"], ifc, rc, have / 1e9, f["size"] / 1e9))
        time.sleep(15)
    return "gave up"

def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    jobs = 4
    for i, x in enumerate(sys.argv):
        if x == "--jobs":
            jobs = int(sys.argv[i + 1]); a.remove(sys.argv[i + 1])
    repo, dest, pats = a[0], a[1], a[2:]
    ifaces = os.environ.get("INK2_DL_IFACES", "").split() or ["lo"]
    files = [f for f in tree(repo) if any(fnmatch.fnmatch(f["path"], p) for p in pats)]
    total = sum(f["size"] for f in files)
    log("%s: %d files, %.1f GB -> %s" % (repo, len(files), total / 1e9, dest))
    if not files:
        log("no file matches"); return 1
    if "--verify-only" in sys.argv:
        res = [(f["path"], verify(f, dest)) for f in files]
    else:
        with ThreadPoolExecutor(jobs) as ex:
            res = list(zip([f["path"] for f in files], ex.map(lambda f: get(repo, f, dest, ifaces), files)))
    bad = [(p, r) for p, r in res if r != "ok"]
    for p, r in bad:
        log("   NOT OK", p, r)
    log("%s: %d of %d files verified" % (repo, len(res) - len(bad), len(res)))
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
