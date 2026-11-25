import sys
sys.path.insert(0, '.')

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

print('ALL-OK')
