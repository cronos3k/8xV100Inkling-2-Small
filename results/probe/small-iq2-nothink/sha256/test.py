import sys
sys.path.insert(0, '.')

import hashlib
from sol import sha256
for n in [0, 1, 3, 55, 56, 57, 63, 64, 65, 119, 120, 1000]:
    d = bytes((i * 37 + 11) % 256 for i in range(n))
    assert sha256(d) == hashlib.sha256(d).hexdigest(), "wrong digest for %d bytes" % n
assert sha256(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

print('ALL-OK')
