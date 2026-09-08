"""A real fix for the `eval()` shortcut both a typical first-pass
implementation of this pattern (a naive `calc` tool) AND Threshold's own
earlier `estimate_claim_payout` tool carry — Throughline is the first
product in this suite to actually close it, not just cite it.

A common piece of introductory material recommends `ast.literal_eval` as a
production-grade alternative to `eval()` — but that recommendation doesn't
actually work for a calculator: verified directly, `ast.literal_eval("12*8")`
raises `ValueError: malformed node or string`, because `literal_eval` only
parses literal constants (plus a narrow carve-out for signed numbers and
complex-number literals), never a `BinOp` like multiplication. This module
implements the fix that recommendation doesn't quite deliver: parse the
expression as a real expression tree (`ast.parse(expr, mode="eval")`), then
walk it ourselves, allowing only numeric constants, `+ - * /`, and unary
+/-. Anything else — names, calls, attribute access, subscripts,
comparisons, string constants — is rejected before it can ever reach
Python's evaluator, because we never call `eval()`, `exec()`, or
`literal_eval()` on the input at all.
"""
import ast
import operator

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class UnsafeExpressionError(ValueError):
    """Raised for anything outside the numeric-arithmetic whitelist."""


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise UnsafeExpressionError(f"only numeric constants are allowed, not {node.value!r}")
        return node.value
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BINOPS:
            raise UnsafeExpressionError(f"operator not allowed: {op_type.__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if op_type is ast.Div and right == 0:
            raise UnsafeExpressionError("division by zero")
        return _ALLOWED_BINOPS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARYOPS:
            raise UnsafeExpressionError(f"unary operator not allowed: {op_type.__name__}")
        return _ALLOWED_UNARYOPS[op_type](_eval_node(node.operand))
    raise UnsafeExpressionError(f"expression element not allowed: {type(node).__name__}")


def safe_eval(expr: str) -> float:
    """Evaluate a plain numeric arithmetic expression (+ - * / and
    parentheses only). Raises UnsafeExpressionError for anything else —
    never falls back to Python's own eval()/literal_eval()."""
    expr = expr.strip()
    if not expr:
        raise UnsafeExpressionError("empty expression")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpressionError(f"could not parse expression: {exc.msg}") from exc
    return _eval_node(tree)
