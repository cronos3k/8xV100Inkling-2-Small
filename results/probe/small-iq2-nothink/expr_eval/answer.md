```python
import math

def evaluate(expr: str) -> float:
    if not isinstance(expr, str):
        raise ValueError("expression must be a string")

    tokens = _tokenize(expr)
    if not tokens:
        raise ValueError("empty expression")

    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def advance():
        nonlocal pos
        tok = tokens[pos]
        pos += 1
        return tok

    def parse_expr():
        node = parse_term()
        while peek() in ('+', '-'):
            op = advance()
            rhs = parse_term()
            node = ('bin', op, node, rhs)
        return node

    def parse_term():
        node = parse_factor()
        while peek() in ('*', '/'):
            op = advance()
            rhs = parse_factor()
            node = ('bin', op, node, rhs)
        return node

    def parse_factor():
        # Unary minus binds looser than ** on its left: -2**2 == -(2**2)
        if peek() == '-':
            advance()
            operand = parse_factor()
            return ('neg', operand)
        if peek() == '+':
            advance()
            return parse_factor()
        return parse_power()

    def parse_power():
        base = parse_atom()
        if peek() == '**':
            advance()
            # Right operand may start with unary minus; ** is right-associative
            exponent = parse_factor()
            return ('bin', '**', base, exponent)
        return base

    def parse_atom():
        tok = peek()
        if tok is None:
            raise ValueError("unexpected end of expression")
        if tok == '(':
            advance()
            node = parse_expr()
            if peek() != ')':
                raise ValueError("missing closing parenthesis")
            advance()
            return node
        if isinstance(tok, float):
            advance()
            return ('num', tok)
        raise ValueError(f"unexpected token: {tok!r}")

    tree = parse_expr()
    if pos != len(tokens):
        raise ValueError(f"unexpected trailing token: {tokens[pos]!r}")

    return _eval_node(tree)


def _tokenize(expr: str):
    tokens = []
    i, n = 0, len(expr)
    while i < n:
        ch = expr[i]
        if ch in ' \t\r\n':
            i += 1
            continue
        if ch.isdigit() or ch == '.':
            j = i
            seen_dot = False
            while j < n and (expr[j].isdigit() or expr[j] == '.'):
                if expr[j] == '.':
                    if seen_dot:
                        raise ValueError("malformed number")
                    seen_dot = True
                j += 1
            text = expr[i:j]
            try:
                value = float(text)
            except ValueError:
                raise ValueError(f"malformed number: {text!r}")
            tokens.append(value)
            i = j
            continue
        if ch == '*' and i + 1 < n and expr[i + 1] == '*':
            tokens.append('**')
            i += 2
            continue
        if ch in '+-*/()':
            tokens.append(ch)
            i += 1
            continue
        raise ValueError(f"invalid character: {ch!r}")
    return tokens


def _eval_node(node):
    kind = node[0]
    if kind == 'num':
        return node[1]
    if kind == 'neg':
        return -_eval_node(node[1])
    _, op, left, right = node
    a = _eval_node(left)
    b = _eval_node(right)
    if op == '+':
        return a + b
    if op == '-':
        return a - b
    if op == '*':
        return a * b
    if op == '/':
        return a / b
    if op == '**':
        try:
            return a ** b
        except OverflowError:
            return math.inf if a >= 0 else -math.inf
    raise ValueError(f"unknown operator: {op!r}")
```