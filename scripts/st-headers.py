#!/usr/bin/env python3
"""st-headers.py REPO OUT_JSON [PATTERN]
Fetch only the safetensors headers (names, dtypes, shapes) of a public Hugging Face repository by HTTP range
requests; no weights are downloaded. Output: {tensor name: {dtype, shape, file}}."""
import fnmatch, json, struct, sys, urllib.request
repo, out = sys.argv[1], sys.argv[2]
pat = sys.argv[3] if len(sys.argv) > 3 else "model-*.safetensors"
def get(url, a, b):
    r = urllib.request.Request(url, headers={"Range": "bytes=%d-%d" % (a, b)})
    return urllib.request.urlopen(r, timeout=120).read()
tree = json.load(urllib.request.urlopen("https://huggingface.co/api/models/%s/tree/main?recursive=true&limit=1000" % repo, timeout=60))
res = {}
for f in sorted(x["path"] for x in tree if x.get("type") == "file" and fnmatch.fnmatch(x["path"], pat)):
    url = "https://huggingface.co/%s/resolve/main/%s" % (repo, f)
    n = struct.unpack("<Q", get(url, 0, 7))[0]
    h = json.loads(get(url, 8, 8 + n - 1))
    for k, v in h.items():
        if k != "__metadata__":
            res[k] = {"dtype": v["dtype"], "shape": v["shape"], "file": f}
    print(f, n, "header bytes,", len(h) - 1, "tensors", flush=True)
json.dump(res, open(out, "w"))
print("total", len(res), "tensors ->", out)
