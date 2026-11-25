```python
import re
from typing import Any, List


_TOKEN_RE = re.compile(r"\(|\)|[^\s()]+")
_INT_RE = re.compile(r"-?\d+")


class Env:
    def __init__(self, parent: "Env | None" = None):
        self.vars = {}
        self.parent = parent

    def lookup(self, name: str) -> Any:
        env = self
        while env is not None:
            if name in env.vars:
                return env.vars[name]
            env = env.parent
        raise NameError(f"undefined symbol: {name}")

    def define(self, name: str, value: Any) -> None:
        self.vars[name] = value


class Closure:
    def __init__(self, params: List[str], body: List[Any], env: Env):
        self.params = list(params)
        self.body = list(body)
        self.env = env

    def __call__(self, *args: Any) -> Any:
        if len(args) != len(self.params):
            raise TypeError(
                f"expected {len(self.params)} arguments, got {len(args)}"
            )
        local = Env(self.env)
        for name, value in zip(self.params, args):
            local.define(name, value)
        return _eval_body(self.body, local)


def _tokenize(src: str) -> List[str]:
    src = re.sub(r";[^\n]*", "", src)
    return _TOKEN_RE.findall(src)


def _parse(tokens: List[str]) -> List[Any]:
    pos = 0

    def parse_expr() -> Any:
        nonlocal pos
        if pos >= len(tokens):
            raise SyntaxError("unexpected end of input")
        tok = tokens[pos]
        pos += 1

        if tok == "(":
            items = []
            while True:
                if pos >= len(tokens):
                    raise SyntaxError("missing )")
                if tokens[pos] == ")":
                    pos += 1
                    return items
                items.append(parse_expr())

        if tok == ")":
            raise SyntaxError("unexpected )")

        if _INT_RE.fullmatch(tok):
            return int(tok)
        return tok

    forms = []
    while pos < len(tokens):
        forms.append(parse_expr())
    return forms


def _ensure_params(params: Any) -> List[str]:
    if not isinstance(params, list):
        raise SyntaxError("parameters must be a list")
    seen = set()
    result = []
    for param in params:
        if not isinstance(param, str):
            raise SyntaxError("parameter names must be symbols")
        if param in seen:
            raise SyntaxError(f"duplicate parameter: {param}")
        seen.add(param)
        result.append(param)
    return result


def _eval_body(body: List[Any], env: Env) -> Any:
    if not body:
        raise SyntaxError("body must contain at least one expression")
    value = None
    for expr in body:
        value = _eval_expr(expr, env)
    return value


def _apply(fn: Any, args: List[Any]) -> Any:
    if isinstance(fn, Closure):
        return fn(*args)
    if callable(fn):
        return fn(*args)
    raise TypeError(f"not a function: {fn!r}")


def _eval_expr(expr: Any, env: Env) -> Any:
    if isinstance(expr, int):
        return expr
    if isinstance(expr, str):
        return env.lookup(expr)
    if not isinstance(expr, list):
        raise TypeError(f"invalid expression: {expr!r}")
    if not expr:
        raise SyntaxError("empty expression")

    head = expr[0]

    if head == "lambda":
        if len(expr) < 3:
            raise SyntaxError("lambda requires parameters and a body")
        params = _ensure_params(expr[1])
        return Closure(params, expr[2:], env)

    if head == "if":
        if len(expr) != 4:
            raise SyntaxError("if requires cond, then, and else")
        cond = _eval_expr(expr[1], env)
        if cond is False:
            return _eval_expr(expr[3], env)
        return _eval_expr(expr[2], env)

    if head == "let":
        if len(expr) < 3:
            raise SyntaxError("let requires bindings and a body")
        bindings = expr[1]
        if not isinstance(bindings, list):
            raise SyntaxError("let bindings must be a list")
        names = []
        values = []
        for binding in bindings:
            if not isinstance(binding, list) or len(binding) != 2:
                raise SyntaxError("each let binding must be (name expr)")
            name = binding[0]
            if not isinstance(name, str):
                raise SyntaxError("let binding name must be a symbol")
            names.append(name)
            values.append(_eval_expr(binding[1], env))
        child = Env(env)
        for name, value in zip(names, values):
            child.define(name, value)
        return _eval_body(expr[2:], child)

    fn = _eval_expr(head, env)
    args = [_eval_expr(arg, env) for arg in expr[1:]]
    return _apply(fn, args)


def _is_define_form(form: Any) -> bool:
    return isinstance(form, list) and len(form) > 0 and form[0] == "define"


def _eval_define(form: List[Any], env: Env) -> None:
    if len(form) < 3:
        raise SyntaxError("define requires a target and a body")

    target = form[1]

    if isinstance(target, str):
        if len(form) != 3:
            raise SyntaxError("(define name expr) takes exactly one expression")
        env.define(target, _eval_expr(form[2], env))
        return

    if isinstance(target, list):
        if not target:
            raise SyntaxError("define function target cannot be empty")
        name = target[0]
        if not isinstance(name, str):
            raise SyntaxError("function name must be a symbol")
        params = _ensure_params(target[1:])
        env.define(name, Closure(params, form[2:], env))
        return

    raise SyntaxError("define target must be a symbol or (name params...)")


def _add(*args: Any) -> Any:
    total = 0
    for arg in args:
        total += arg
    return total


def _mul(*args: Any) -> Any:
    total = 1
    for arg in args:
        total *= arg
    return total


def _sub(*args: Any) -> Any:
    if len(args) == 1:
        return -args[0]
    if len(args) == 2:
        return args[0] - args[1]
    raise TypeError("- expects one or two arguments")


def _lt(*args: Any) -> bool:
    if len(args) != 2:
        raise TypeError("< expects two arguments")
    return bool(args[0] < args[1])


def _eq(*args: Any) -> bool:
    if len(args) != 2:
        raise TypeError("= expects two arguments")
    return bool(args[0] == args[1])


def _make_global_env() -> Env:
    env = Env()
    env.define("+", _add)
    env.define("*", _mul)
    env.define("-", _sub)
    env.define("<", _lt)
    env.define("=", _eq)
    return env


def run(src: str) -> list:
    forms = _parse(_tokenize(src))
    env = _make_global_env()
    values = []
    for form in forms:
        if _is_define_form(form):
            _eval_define(form, env)
        else:
            values.append(_eval_expr(form, env))
    return values
```