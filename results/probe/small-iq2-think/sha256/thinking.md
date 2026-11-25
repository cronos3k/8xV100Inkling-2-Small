We need answer with one Python code block and nothing else. Need implement SHA-256 from scratch no imports. Need produce correct code. Need think carefully.

We need write sha256(data: bytes) -> str lowercase hex digest. No imports at all. Need implement constants, padding, compression.

Need ensure correctness. Let's craft code.

SHA-256 algorithm:
- h initial: 6a09e667 bb67ae85 3c6ef372 a54ff53a 510e527f 9b05688c 1f83d9ab 5be0cd19
- k 64 constants.
- Preprocess: message bytes, append 0x80, pad zeros until length ≡ 56 mod 64, append 8-byte big-endian bit length.
- Process 64-byte chunks: w[0:16] big endian words; for t 16..63: s0=rotr(w[t-15],7)^rotr(w[t-15],18)^(w[t-15]>>3); s1=rotr(w[t-2],17)^rotr(w[t-2],19)^(w[t-2]>>10); w[t]=(w[t-16]+s0+w[t-7]+s1)&0xffffffff.
- a..h = h0..h7; loop t: S1=rotr(e,6)^rotr(e,11)^rotr(e,25); ch=(e&f)^((~e)&g); temp1=(h+S1+ch+k[t]+w[t])&mask; S0=rotr(a,2)^rotr(a,13)^rotr(a,22); maj=(a&b)^(a&c)^(b&c); temp2=(S0+maj)&mask; h=g; g=f; f=e; e=(d+temp1)&mask; d=c; c=b; b=a; a=(temp1+temp2)&mask.
- add to h.
- digest hex format each h as 08x.

Need no imports. Use bytes operations. data: bytes. Could accept only bytes. Need maybe handle bytearray? signature bytes.

Need output exactly one code block and nothing else. Ensure code block contains only code. No explanations.

Need be careful with ~e in Python negative; use (~e)&0xffffffff or (e ^ 0xffffffff)&g. Use ch=(e & f) ^ ((~e & 0xffffffff) & g) or (e & f) ^ (~e & g) since ~e & g in Python: ~e is negative but bitwise & with g yields correct? In Python, -x & y = (~x)&y? Let's recall: Python integers are infinite two's complement. ~e = -e-1. (~e) & g where g 0..2^32-1 yields bits of ~e within g's bits, equivalent to (~e & 0xffffffff)&g because g only has low 32 bits. Yes (~e)&g works and yields nonnegative. Good.

Need constants exact. Let's list K:
428a2f98 71374491 b5c0fbcf e9b5dba5 3956c25b 59f111f1 923f82a4 ab1c5ed5
d807aa98 12835b01 243185be 550c7dc3 72be5d74 80deb1fe 9bdc06a7 c19bf174
e49b69c1 efbe4786 0fc19dc6 240ca1cc 2de92c6f 4a7484aa 5cb0a9dc 76f988da
983e5152 a831c66d b00327c8 bf597fc7 c6e00bf3 d5a79147 06ca6351 14292967
27b70a85 2e1b2138 4d2c6dfc 53380d13 650a7354 766a0abb 81c2c92e 92722c85
a2bfe8a1 a81a664b c24b8b70 c76c51a3 d192e819 d6990624 f40e3585 106aa070
19a4c116 1e376c08 2748774c 34b0bcb5 391c0cb3 4ed8aa4a 5b9cca4f 682e6ff3
748f82ee 78a5636f 84c87814 8cc70208 90befffa a4506ceb bef9a3f7 c67178f2
Need ensure all 64.

Initial H:
6a09e667, bb67ae85, 3c6ef372, a54ff53a, 510e527f, 9b05688c, 1f83d9ab, 5be0cd19.

Padding: bit_len = len(data)*8; msg = bytearray(data); msg.append(0x80); while len(msg)%64 != 56: msg.append(0); msg += bit_len.to_bytes(8,'big'). No imports, to_bytes is method okay.

rotr function nested or inline. Use def _rotr(x,n): return ((x >> n) | (x << (32-n))) & 0xffffffff.

Hex: ''.join(f'{x:08x}' for x in h) uses f-string no import. Fine.

Need final code only. Could include if __name__? Not necessary. Just function and constants. No imports.

Need ensure no accidental import. Code block with python. Final only code block.