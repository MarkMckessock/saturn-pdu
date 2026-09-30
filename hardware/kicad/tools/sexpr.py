"""Minimal S-expression reader/writer for KiCad files."""
import re


class Q(str):
    """A quoted string atom."""


_TOK = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


def parse(text):
    stack = [[]]
    pos = 0
    while True:
        m = _TOK.match(text, pos)
        if not m:
            break
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            done = stack.pop()
            stack[-1].append(done)
        elif m.group(3) is not None:
            stack[-1].append(Q(re.sub(r'\\(.)', r'\1', m.group(3))))
        else:
            stack[-1].append(m.group(4))
    return stack[0][0]


def _atom(a):
    if isinstance(a, Q):
        return '"' + a.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if isinstance(a, float):
        s = f'{a:.4f}'.rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    return str(a)


def dump(node, indent=0):
    if not isinstance(node, list):
        return _atom(node)
    if all(not isinstance(x, list) for x in node):
        return '(' + ' '.join(_atom(x) for x in node) + ')'
    pad = '\t' * (indent + 1)
    head = []
    rest = []
    for x in node:
        if not rest and not isinstance(x, list):
            head.append(_atom(x))
        else:
            rest.append(x)
    out = '(' + ' '.join(head)
    for x in rest:
        out += '\n' + pad + dump(x, indent + 1)
    return out + '\n' + '\t' * indent + ')'


def find(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def find1(node, key):
    r = find(node, key)
    return r[0] if r else None
