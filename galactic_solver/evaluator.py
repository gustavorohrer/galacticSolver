from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict
import ast

ALLOWED_BIN_OPS = {
    ast.Add, ast.Sub, ast.Mult, ast.Div
}
ALLOWED_UNARY_OPS = {ast.UAdd, ast.USub}


def round10(x: Decimal) -> Decimal:
    return x.quantize(Decimal('0.0000000001'), rounding=ROUND_HALF_UP)


def _to_decimal(v: Any) -> Decimal:
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float)):
        return Decimal(str(v))
    if isinstance(v, str):
        # If a string leaks here outside of len(), we try len as a fallback
        return Decimal(len(v))
    raise ValueError("Unsupported value type for Decimal conversion")


def eval_expression(expression: str, variables: Dict[str, Any]) -> Decimal:
    tree = ast.parse(expression, mode='eval')

    def eval_node(node) -> Any:
        if isinstance(node, ast.Expression):
            return eval_node(node.body)
        if isinstance(node, ast.Num):  # Python <3.8
            return Decimal(str(node.n))
        if isinstance(node, ast.Constant):  # Python 3.8+
            if isinstance(node.value, (int, float)):
                return Decimal(str(node.value))
            if isinstance(node.value, str):
                return node.value
            raise ValueError("Unsupported constant type")
        if isinstance(node, ast.Name):
            if node.id not in variables:
                raise ValueError(f"Unknown variable {node.id}")
            return variables[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_BIN_OPS:
            left = eval_node(node.left)
            right = eval_node(node.right)
            l = _to_decimal(left)
            r = _to_decimal(right)
            if isinstance(node.op, ast.Add):
                return l + r
            if isinstance(node.op, ast.Sub):
                return l - r
            if isinstance(node.op, ast.Mult):
                return l * r
            if isinstance(node.op, ast.Div):
                if r == 0:
                    raise ZeroDivisionError("Division by zero in expression")
                return l / r
        if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_UNARY_OPS:
            operand = _to_decimal(eval_node(node.operand))
            if isinstance(node.op, ast.UAdd):
                return operand
            if isinstance(node.op, ast.USub):
                return -operand
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'len' and len(node.args) == 1:
                val = eval_node(node.args[0])
                if isinstance(val, str):
                    return Decimal(len(val))
                # If val is not string, coerce to string length safely
                return Decimal(len(str(val)))
            raise ValueError("Only len(x) function is allowed")
        raise ValueError("Unsupported expression element")

    result = eval_node(tree)
    return round10(_to_decimal(result))
