import sys
sys.path.insert(0, '.')

from sol import run
assert run("(+ 1 2)") == [3]
assert run("(define x 5) (* x x)") == [25]
assert run("(define (fact n) (if (< n 2) 1 (* n (fact (- n 1))))) (fact 10)") == [3628800]
assert run("(define fib (lambda (n) (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2)))))) (fib 15)") == [610]
assert run("(define (make-adder n) (lambda (x) (+ x n))) (define add5 (make-adder 5)) (add5 10) ((make-adder 1) 1)") == [15, 2]
assert run("(let ((x 2) (y 3)) (* x y))") == [6]
assert run("(define x 1) (define (f) x) (let ((x 99)) (f))") == [1], "scoping must be lexical"
assert run("(if (= 1 1) 10 20) (if (< 2 1) 10 20) (if 0 1 2)") == [10, 20, 1]
assert run("(- 5) (- 10 3) (+ 1 2 3 4) (+ -3 5) (* 2 3 4)") == [-5, 7, 10, 2, 24]
assert run("((lambda (f x) (f (f x))) (lambda (y) (* y y)) 3)") == [81]
assert run("(define (count n acc) (if (= n 0) acc (count (- n 1) (+ acc 1)))) (count 150 0)") == [150]
assert run("(define (compose f g) (lambda (x) (f (g x))))\n(define inc (lambda (x) (+ x 1)))\n(define dbl (lambda (x) (* x 2)))\n((compose inc dbl) 5) ((compose dbl inc) 5)") == [11, 12]
assert run("(< 1 2)") == [True]

print('ALL-OK')
