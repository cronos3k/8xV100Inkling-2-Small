import sys
sys.path.insert(0, '.')

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

print('ALL-OK')
