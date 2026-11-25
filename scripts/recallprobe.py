#!/usr/bin/env python3
"""recallprobe.py OUTDIR PORT MODEL [--jobs N]

Exact-recall probe: tables a programmer's model knows by heart (signal and errno numbers, syscall numbers,
hash constants, the AES S-box, file magic numbers, code points, ports, digits of pi). Low-bit weights lose
this kind of rarely used exact knowledge first, long before fluent code breaks. Every item is checked
against ground truth taken from this machine (Python modules, kernel headers, computed tables).
Greedy, thinking off. Prints the share of correct items per table.
"""
import concurrent.futures, decimal, errno, json, os, re, signal, sys, time, unicodedata, urllib.request

A = [x for x in sys.argv[1:] if not x.startswith("--")]
OUT, PORT, MODEL = A[0], A[1], A[2]
JOBS = int(next((sys.argv[i + 1] for i, x in enumerate(sys.argv) if x == "--jobs"), "4"))

J = " Reply with one JSON object in a code block and nothing else."
Q = []


def table(name, question, truth, norm=lambda v: v):
    Q.append((name, question, truth, norm))


def as_int(v):
    try:
        return int(str(v).strip(), 0) if isinstance(v, str) else int(v)
    except Exception:
        return None


def as_hex(v):
    return re.sub(r"[^0-9a-f]", "", str(v).lower().replace("0x", "").replace("u+", "")).lstrip("0") or "0"


# --- tables whose truth this machine knows
SIG = "SIGHUP SIGINT SIGQUIT SIGILL SIGTRAP SIGABRT SIGBUS SIGFPE SIGKILL SIGUSR1 SIGSEGV SIGUSR2 SIGPIPE SIGALRM SIGTERM SIGCHLD SIGCONT SIGSTOP SIGTSTP SIGTTIN SIGTTOU SIGURG SIGXCPU SIGXFSZ SIGVTALRM SIGPROF SIGWINCH SIGIO SIGPWR SIGSYS".split()
table("signals", "Linux on x86-64: give the signal number of each of these signals: " + ", ".join(SIG) + ". Keys are the names, values the numbers." + J,
      {n: int(getattr(signal, n)) for n in SIG}, as_int)

ERR = "EPERM ENOENT ESRCH EINTR EIO ENXIO E2BIG ENOEXEC EBADF ECHILD EAGAIN ENOMEM EACCES EFAULT EBUSY EEXIST EXDEV ENODEV ENOTDIR EISDIR EINVAL ENFILE EMFILE ENOTTY EFBIG ENOSPC ESPIPE EROFS EMLINK EPIPE EDOM ERANGE EDEADLK ENAMETOOLONG ENOSYS ENOTEMPTY ELOOP EADDRINUSE ECONNREFUSED ETIMEDOUT ECONNRESET ENOTCONN EHOSTUNREACH EINPROGRESS EALREADY ENOTSOCK EMSGSIZE EPROTONOSUPPORT EAFNOSUPPORT ENETUNREACH".split()
table("errno", "Linux on x86-64: give the numeric value of each of these errno constants: " + ", ".join(ERR) + ". Keys are the names, values the numbers." + J,
      {n: getattr(errno, n) for n in ERR}, as_int)

SYS = "read write open close stat fstat lstat poll lseek mmap mprotect munmap brk rt_sigaction ioctl pipe select sched_yield dup dup2 nanosleep getpid socket connect accept sendto recvfrom bind listen clone fork vfork execve exit wait4 kill fcntl getdents getcwd chdir rename mkdir rmdir unlink chmod getuid ptrace futex epoll_create epoll_wait epoll_ctl openat accept4 epoll_create1 pipe2 getrandom memfd_create execveat io_uring_setup clone3".split()
hdr = "/usr/include/x86_64-linux-gnu/asm/unistd_64.h"
if os.path.exists(hdr):
    nums = dict(re.findall(r"#define __NR_(\w+)\s+(\d+)", open(hdr).read()))
    table("syscalls", "Linux x86-64 system call numbers (as in asm/unistd_64.h): give the number of each of: " + ", ".join(SYS) + ". Keys are the names, values the numbers." + J,
          {n: int(nums[n]) for n in SYS if n in nums}, as_int)

K256 = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2]


def check_k256():
    # the table above is itself checked: K[i] = frac(cbrt(prime_i)) * 2^32
    decimal.getcontext().prec = 60
    ps = [p for p in range(2, 400) if all(p % d for d in range(2, int(p ** 0.5) + 1))][:64]
    for p, k in zip(ps, K256):
        r = decimal.Decimal(p) ** (decimal.Decimal(1) / 3)
        assert int((r - int(r)) * 2 ** 32) == k, hex(k)


check_k256()
table("sha256_K", "List the 64 round constants K[0..63] of SHA-256 in order. Keys are the decimal indices \"0\" to \"63\", values hex strings such as \"0x428a2f98\"." + J,
      {str(i): "%x" % k for i, k in enumerate(K256)}, as_hex)


def aes_sbox():
    def mul(a, b):
        r = 0
        while b:
            if b & 1:
                r ^= a
            a = (a << 1) ^ (0x11b if a & 0x80 else 0)
            b >>= 1
        return r
    inv = [0] + [next(y for y in range(1, 256) if mul(x, y) == 1) for x in range(1, 256)]
    out = []
    for x in range(256):
        b = inv[x]
        s = b
        for i in range(1, 5):
            s ^= ((b << i) | (b >> (8 - i))) & 0xff
        out.append(s ^ 0x63)
    return out


SBOX = aes_sbox()
assert SBOX[0] == 0x63 and SBOX[1] == 0x7c and SBOX[0x53] == 0xed and SBOX[255] == 0x16
for lo in (0, 128):
    table("aes_sbox_%d" % lo, "Give the AES (Rijndael) forward S-box values for the inputs 0x%02x to 0x%02x. Keys are the inputs as two-digit lowercase hex strings (\"%02x\" ... \"%02x\"), values the outputs as two-digit hex strings." % (lo, lo + 127, lo, lo + 127) + J,
          {"%02x" % i: "%x" % SBOX[i] for i in range(lo, lo + 128)}, as_hex)


def crc_table():
    t = []
    for n in range(256):
        c = n
        for _ in range(8):
            c = (c >> 1) ^ (0xEDB88320 if c & 1 else 0)
        t.append(c)
    return t


CRC = crc_table()
table("crc32_table", "Give the first 32 entries (index 0 to 31) of the standard reflected CRC-32 lookup table (polynomial 0xEDB88320, as in zlib). Keys are the decimal indices, values hex strings." + J,
      {str(i): "%x" % CRC[i] for i in range(32)}, as_hex)

MD5S = [7, 12, 17, 22] * 4 + [5, 9, 14, 20] * 4 + [4, 11, 16, 23] * 4 + [6, 10, 15, 21] * 4
MISC = {"md5_shift_%d" % i: MD5S[i] for i in (0, 1, 2, 3, 16, 17, 18, 19, 32, 33, 34, 35, 48, 49, 50, 51)}
MISC.update({"sha1_K_%d" % i: v for i, v in enumerate((0x5a827999, 0x6ed9eba1, 0x8f1bbcdc, 0xca62c1d6))})
MISC.update({"sha1_H_%d" % i: v for i, v in enumerate((0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476, 0xc3d2e1f0))})
MISC.update({"sha256_H_%d" % i: v for i, v in enumerate((0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19))})
MISC.update({"fnv1a_32_offset_basis": 0x811c9dc5, "fnv1a_32_prime": 0x01000193, "fnv1a_64_offset_basis": 0xcbf29ce484222325, "fnv1a_64_prime": 0x100000001b3,
             "crc32c_reflected_polynomial": 0x82f63b78, "crc16_ccitt_polynomial": 0x1021, "adler32_modulus": 65521, "murmur3_32_c1": 0xcc9e2d51, "murmur3_32_c2": 0x1b873593,
             "golden_ratio_32bit_hash_constant": 0x9e3779b9, "xorshift32_shift_a": 13, "xorshift32_shift_b": 17, "xorshift32_shift_c": 5,
             "numerical_recipes_lcg_multiplier": 1664525, "numerical_recipes_lcg_increment": 1013904223, "minstd_multiplier": 48271, "mersenne_twister_mt19937_matrix_a": 0x9908b0df})
table("hash_constants", "Give these constants used in well-known algorithms. md5_shift_N is the per-round left-rotation amount of MD5 step N (0-based); sha1_K_N the four SHA-1 round constants; sha1_H_N and sha256_H_N the initial hash values. Keys exactly as listed, values as hex strings or numbers: " + ", ".join(MISC) + "." + J,
      {k: "%x" % v for k, v in MISC.items()}, as_hex)

MAGIC = {"PNG (8 bytes)": "89504e470d0a1a0a", "ZIP local file header (4 bytes)": "504b0304", "GZIP (2 bytes)": "1f8b", "ELF (4 bytes)": "7f454c46", "PDF (4 bytes)": "25504446",
         "JPEG (first 3 bytes)": "ffd8ff", "GIF89a (6 bytes)": "474946383961", "BMP (2 bytes)": "424d", "7z (6 bytes)": "377abcaf271c", "XZ (6 bytes)": "fd377a585a00",
         "Zstandard frame (4 bytes, as stored in the file)": "28b52ffd", "bzip2 (3 bytes)": "425a68", "TIFF little-endian (4 bytes)": "49492a00", "WebAssembly (4 bytes)": "0061736d",
         "Java class file (4 bytes)": "cafebabe", "SQLite 3 database (16 bytes)": "53514c69746520666f726d6174203300", "Ogg (4 bytes)": "4f676753", "FLAC (4 bytes)": "664c6143",
         "LZ4 frame (4 bytes, as stored in the file)": "04224d18", "RAR 5 (8 bytes)": "526172211a070100"}
table("magic_bytes", "Give the magic bytes at the start of each of these file formats as a hex string without spaces: " + "; ".join(MAGIC) + ". Keys exactly as listed." + J,
      MAGIC, lambda v: re.sub(r"[^0-9a-f]", "", str(v).lower().replace("0x", "")))

UNI = ["EURO SIGN", "SNOWMAN", "GREEK SMALL LETTER LAMDA", "CYRILLIC CAPITAL LETTER ZHE", "RIGHTWARDS ARROW", "INFINITY", "BLACK HEART SUIT", "EM DASH", "NO-BREAK SPACE",
       "ZERO WIDTH JOINER", "REPLACEMENT CHARACTER", "ZERO WIDTH NO-BREAK SPACE", "PILE OF POO", "GRINNING FACE", "LATIN SMALL LETTER SHARP S", "DEGREE SIGN", "MICRO SIGN", "BULLET",
       "HORIZONTAL ELLIPSIS", "CHECK MARK", "MULTIPLICATION SIGN", "SECTION SIGN", "COPYRIGHT SIGN", "TRADE MARK SIGN", "HEBREW LETTER ALEF", "ARABIC LETTER ALEF", "HIRAGANA LETTER A",
       "KATAKANA LETTER A", "LEFT-TO-RIGHT MARK", "SOFT HYPHEN", "BOX DRAWINGS LIGHT HORIZONTAL", "FULL BLOCK", "WHITE SMILING FACE", "LATIN CAPITAL LETTER A WITH DIAERESIS", "RIGHT SINGLE QUOTATION MARK", "N-ARY SUMMATION"]
table("unicode", "Give the Unicode code point of each of these characters, by official name, as a string such as \"U+20AC\": " + "; ".join(UNI) + ". Keys are the names." + J,
      {n: "%x" % ord(unicodedata.lookup(n)) for n in UNI}, as_hex)

PORTS = {"ssh": 22, "telnet": 23, "smtp": 25, "dns": 53, "tftp": 69, "http": 80, "kerberos": 88, "pop3": 110, "ntp": 123, "imap": 143, "snmp": 161, "bgp": 179, "ldap": 389, "https": 443,
         "smb over tcp (microsoft-ds)": 445, "syslog (udp)": 514, "smtp submission": 587, "ldaps": 636, "rsync": 873, "imaps": 993, "pop3s": 995, "ms sql server": 1433, "oracle listener": 1521,
         "mqtt": 1883, "nfs": 2049, "zookeeper": 2181, "etcd client": 2379, "mysql": 3306, "rdp": 3389, "postgresql": 5432, "amqp": 5672, "vnc display 0": 5900, "redis": 6379,
         "kubernetes api server": 6443, "consul http": 8500, "cassandra cql": 9042, "kafka": 9092, "elasticsearch http": 9200, "git protocol": 9418, "memcached": 11211, "mongodb": 27017, "wireguard default": 51820}
table("ports", "Give the default port number of each service: " + "; ".join(PORTS) + ". Keys exactly as listed, values numbers." + J, PORTS, as_int)


def digits_pi(n):
    decimal.getcontext().prec = n + 20
    D = decimal.Decimal

    def atan_inv(x):
        t = D(1) / x
        s, k, x2 = t, 1, x * x
        while True:
            t = -t / x2
            k += 2
            d = t / k
            if abs(d) < D(10) ** -(n + 15):
                return s
            s += d
    return str(4 * (4 * atan_inv(D(5)) - atan_inv(D(239))))[2:n + 2]


decimal.getcontext().prec = 120
DIG = {"pi": digits_pi(100), "e": str(decimal.Decimal(1).exp())[2:82], "sqrt2": str(decimal.Decimal(2).sqrt())[2:62]}
assert DIG["pi"].startswith("14159265358979323846264338327950288419716939937510")


def check_digits(ans):
    m = re.search(r"\{.*\}", ans, re.S)
    try:
        o = json.loads(m.group(0))
    except Exception:
        return 0, sum(len(v) for v in DIG.values()), "unparseable"
    good = 0
    notes = []
    for k, want in DIG.items():
        got = re.sub(r"\D", "", str(o.get(k, "")).split(".", 1)[-1])
        n = 0
        while n < min(len(got), len(want)) and got[n] == want[n]:
            n += 1
        good += n
        notes.append("%s %d/%d" % (k, n, len(want)))
    return good, sum(len(v) for v in DIG.values()), ", ".join(notes)


def ask(prompt):
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 6000, "temperature": 0, "seed": 1,
            "reasoning_effort": "none", "chat_template_kwargs": {"reasoning_effort": "none"}}
    req = urllib.request.Request("http://127.0.0.1:%s/v1/chat/completions" % PORT, json.dumps(body).encode(), {"content-type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=3600))
    return r["choices"][0]["message"].get("content") or ""


def run_table(q):
    name, question, truth, norm = q
    ans = ask(question)
    open(os.path.join(OUT, name + ".md"), "w").write(ans)
    m = re.search(r"\{.*\}", ans, re.S)
    try:
        o = json.loads(m.group(0))
    except Exception:
        return name, 0, len(truth), "unparseable answer"
    low = {str(k).strip().lower(): v for k, v in o.items()}
    wrong = []
    for k, want in truth.items():
        got = low.get(str(k).lower())
        if got is None or norm(got) != norm(want):
            wrong.append("%s=%s (is %s)" % (k, got, want))
    return name, len(truth) - len(wrong), len(truth), "; ".join(wrong[:6])


def run_digits(_):
    ans = ask("Give the decimal digits after the decimal point of pi (100 digits), e (80 digits) and the square root of 2 (60 digits), as strings of digits. Keys: pi, e, sqrt2." + J)
    open(os.path.join(OUT, "digits.md"), "w").write(ans)
    g, n, note = check_digits(ans)
    return "digits", g, n, note


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    tg = tn = 0
    with concurrent.futures.ThreadPoolExecutor(JOBS) as ex:
        futs = [ex.submit(run_table, q) for q in Q] + [ex.submit(run_digits, None)]
        for f in futs:
            name, g, n, note = f.result()
            tg += g
            tn += n
            print("%-16s %4d of %4d  %5.1f %%  %s" % (name, g, n, 100.0 * g / n, note[:260]), flush=True)
    print("RECALL %d of %d items correct = %.1f %%, %.0f s wall" % (tg, tn, 100.0 * tg / tn, time.time() - t0))
