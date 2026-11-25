import sys
sys.path.insert(0, '.')

import bisect, copy
from sol import lower_bound, merge_k
for a in [[], [1], [1, 2, 2, 3, 5], [2, 2, 2], [1, 3, 5, 7, 9, 11]]:
    for x in range(-1, 13):
        assert lower_bound(a, x) == bisect.bisect_left(a, x), (a, x, lower_bound(a, x))
for ls in [[[1, 4, 7], [], [2, 2, 9], [3]], [], [[], []], [[5]], [[1, 1], [1, 1], [0]], [[3, 4], [1, 2], [2, 3]]]:
    keep = copy.deepcopy(ls)
    assert merge_k(ls) == sorted(v for l in keep for v in l), ls
    assert ls == keep, "arguments were modified"

print('ALL-OK')
