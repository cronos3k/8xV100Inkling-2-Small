import re

class _Closure:
    def __init__(self, params, body, env):
        self.params = params
        self.body = body
        self.env = env

class _Env:
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent
    def lookup(self, name):
        env = self
        while env is not None:
            if name in env.vars:
                return env.vars[name]
            env = env.parent
        raise NameError(f"unbound symbol: {name}")
    def define(self, name, value):
        self.vars[name] = value

def _tokenize(src):
    src = re.sub(r';[^\n]*', '', src)
    return re.findall(r'\(|\)|[^\s()]+', src)

def _parse(tokens):
    if not tokens:
        raise SyntaxError("unexpected end of input")
    tok = tokens.pop(0)
    if tok == '(':
        lst = []
        while tokens and tokens[0] != ')':
            lst.append(_parse(tokens))
        if not tokens:
            raise SyntaxError("missing closing parenthesis")
        tokens.pop(0)
        return lst
    if tok == ')':
        raise SyntaxError("unexpected )")
    try:
        return int(tok)
    except ValueError:
        return tok

def _parse_all(src):
    tokens = _tokenize(src)
    forms = []
    while tokens:
        forms.append(_parse(tokens))
    return forms

def _eval(node, env):
    if isinstance(node, int):
        return node
    if isinstance(node, str):
        return env.lookup(node)
    if not isinstance(node, list) or not node:
        raise SyntaxError("invalid form")
    head = node[0]
    if head == 'define':
        target = node[1]
        if isinstance(target, list):
            name = target[0]
            params = target[1:]
            body = node[2]
            env.define(name, _Closure(params, body, env))
        else:
            env.define(target, _eval(node[2], env))
        return None
    if head == 'lambda':
        return _Closure(node[1], node[2], env)
    if head == 'if':
        cond = _eval(node[1], env)
        if cond is False:
            return _eval(node[3], env)
        return _eval(node[2], env)
    if head == 'let':
        new_env = _Env(env)
        for binding in node[1]:
            new_env.define(binding[0], _eval(binding[1], env))
        return _eval(node[2], new_env)
    func = _eval(head, env)
    args = [_eval(a, env) for a in node[1:]]
    return _apply(func, args)

def _apply(func, args):
    if isinstance(func, _Closure):
        call_env = _Env(func.env)
        for p, a in zip(func.params, args):
            call_env.define(p, a)
        return _eval(func.body, call_env)
    return func(*args)

def _make_builtins():
    return {
        '+': lambda *a: sum(a),
        '*': lambda *a: __import__('math').prod(a),
        '-': lambda a, b=None: -a if b is None else a - b,
        '<': lambda a, b: a < b,
        '=': lambda a, b: a == b,
    }

def run(src: str) -> list:
    global_env = _Env()
    for name, fn in _make_builtins().items():
        global_env.define(name, fn)
    results = []
    for form in _parse_all(src):
        if isinstance(form, list) and form and form[0] == 'define':
            _eval(form, global_env)
            continue
        results.append(_eval(form, global_env))
    return results
