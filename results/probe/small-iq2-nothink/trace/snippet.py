def make():
    fs = []
    for i in range(3):
        fs.append(lambda x, i=i: x + i)
    gs = [lambda x: x * j for j in range(3)]
    return fs, gs

fs, gs = make()
a = [f(10) for f in fs]
b = [g(10) for g in gs]

def app(x, acc=[]):
    acc.append(x)
    return acc

c = app(1); d = app(2)
print(a, b, c is d, len(d))
print(7 // -2, -7 % 3, round(2.5), round(3.5), 0.1 + 0.2 == 0.3)
s = "abcdef"
print(s[::-2], s[-2:1:-1], sorted({3: 'a', 1: 'b'}), [*map(lambda p: p[0] * p[1], zip("ab", (2, 1)))])
