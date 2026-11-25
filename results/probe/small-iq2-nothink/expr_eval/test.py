import sys
sys.path.insert(0, '.')

from sol import evaluate
for e in ["1+2*3", "-2**2", "2**3**2", "(1+2)*(3-4)/5", " 3.5 * -2 ", "--3", "2*-3", "10/4", "((2))", "2**-1", "-(3+4)*2", "8/2/2", "2-3-4", "1.5+0.5", "2**-2**2", "-(-(1))", "7 - -2"]:
    got, want = evaluate(e), eval(e)
    assert abs(got - want) < 1e-9, (e, got, want)
for e in ["1+", "(1", "2 3", "", "1+*2", "abc", "1)", "()", "2**", "1 + (2 * 3"]:
    try:
        evaluate(e)
    except ValueError:
        continue
    raise AssertionError("no ValueError for %r" % e)

print('ALL-OK')
