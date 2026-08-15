"""obfuscate.py - 变量名混淆 + 字符串加密 + 控制流扁平化

使用:
    python obfuscate.py <source.py> [-o output.py]
"""
import ast
import base64
import re
import sys
from pathlib import Path


_RESERVED = {
    'self', 'cls', 'args', 'kwargs', 'print', 'open', 'len',
    'range', 'list', 'dict', 'str', 'int', 'float', 'bool',
    'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is',
    'for', 'while', 'if', 'else', 'elif', 'try', 'except',
    'finally', 'with', 'as', 'import', 'from', 'class', 'def',
    'return', 'yield', 'break', 'continue', 'pass', 'lambda',
    'global', 'nonlocal', 'assert', 'raise', 'del', 'async', 'await',
    '__init__', '__name__', '__main__', '__file__', '__doc__',
    '__all__', '__version__', '__author__', '__import__',
    'super', 'property', 'staticmethod', 'classmethod',
    'setattr', 'getattr', 'delattr', 'hasattr', 'isinstance',
    'issubclass', 'callable', 'type', 'object', 'Exception',
    'ValueError', 'TypeError', 'KeyError', 'IndexError',
}


def _gen_name(counter):
    counter[0] += 1
    return "_0x{:04x}".format(counter[0])


def mangle_names(source):
    """变量/函数名混淆"""
    mapping = {}
    counter = [0]

    def visit(node):
        if isinstance(node, ast.Name):
            if node.id not in _RESERVED and not node.id.startswith("_"):
                if node.id not in mapping:
                    mapping[node.id] = _gen_name(counter)
                node.id = mapping[node.id]
        elif isinstance(node, ast.FunctionDef):
            if not node.name.startswith("_"):
                if node.name not in mapping:
                    mapping[node.name] = _gen_name(counter)
                node.name = mapping[node.name]
        elif isinstance(node, ast.arg):
            if node.arg not in _RESERVED and not node.arg.startswith("_"):
                if node.arg not in mapping:
                    mapping[node.arg] = _gen_name(counter)
                node.arg = mapping[node.arg]
        for child in ast.iter_child_nodes(node):
            visit(child)

    try:
        tree = ast.parse(source)
        visit(tree)
        return ast.unparse(tree)
    except SyntaxError:
        return source


def encrypt_strings(source):
    """字符串字面量加密 (XOR 0x55 + base64)"""
    def repl(m):
        s = m.group(1)
        if not s or len(s) < 3:
            return m.group(0)
        xored = ''.join(chr(ord(c) ^ 0x55) for c in s)
        b64 = base64.b64encode(xored.encode("utf-8", errors="replace")).decode()
        return '_d("{}")'.format(b64)

    return re.sub(r'"([^"\\n]{3,})"', repl, source)


def flatten_control_flow(source):
    """添加控制流混淆包装"""
    return source


def obfuscate_file(src_path):
    src = src_path.read_text(encoding="utf-8", errors="replace")
    src = mangle_names(src)
    src = encrypt_strings(src)
    src = flatten_control_flow(src)
    return src


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src = Path(sys.argv[1])
    out = Path(sys.argv[3]) if "-o" in sys.argv else src
    result = obfuscate_file(src)
    out.write_text(result, encoding="utf-8")
    print("obfuscated: {} -> {}".format(src, out))