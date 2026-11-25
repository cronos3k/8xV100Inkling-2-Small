import sys
sys.path.insert(0, '.')

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

print('ALL-OK')
