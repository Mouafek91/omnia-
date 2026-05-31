"""
Safe expression language with dimensional analysis.
AST-walked, no eval/exec.
"""
from __future__ import annotations
import ast
import math
import operator
from dataclasses import dataclass
from typing import Any, Dict

from .units import Unit, Dimension, lookup_unit, DIMENSIONLESS, BOOLEAN, check_additive_compat, DimensionError


class ExpressionError(Exception):
    pass


BINOPS = {
    ast.Add: ("+", operator.add, "add"),
    ast.Sub: ("-", operator.sub, "add"),
    ast.Mult: ("*", operator.mul, "mul"),
    ast.Div: ("/", operator.truediv, "div"),
    ast.Pow: ("**", operator.pow, "pow"),
    ast.Mod: ("%", operator.mod, "mod"),
}
UNARYOPS = {
    ast.UAdd: ("+", operator.pos),
    ast.USub: ("-", operator.neg),
    ast.Not: ("not", operator.not_),
}
CMPOPS = {
    ast.Eq: ("==", operator.eq), ast.NotEq: ("!=", operator.ne),
    ast.Lt: ("<", operator.lt),  ast.LtE: ("<=", operator.le),
    ast.Gt: (">", operator.gt),  ast.GtE: (">=", operator.ge),
}
FUNCTIONS = {
    "abs": (abs, 1), "sqrt": (math.sqrt, 1),
    "log": (math.log, 1), "exp": (math.exp, 1),
    "sin": (math.sin, 1), "cos": (math.cos, 1),
    "min": (min, 2), "max": (max, 2), "pow": (pow, 2),
}
FORBIDDEN = {
    "exec", "eval", "open", "compile", "getattr", "setattr",
    "delattr", "lambda", "class", "def", "global", "nonlocal",
    "yield", "async", "await", "__",
}


class _NameCollector(ast.NodeVisitor):
    def __init__(self):
        self.names: set[str] = set()
    def visit_Name(self, node: ast.Name):
        if node.id.startswith("_"):
            raise ExpressionError(f"Private name forbidden: {node.id}")
        self.names.add(node.id)
    def visit_Attribute(self, node):
        raise ExpressionError("Attribute access forbidden")
    def visit_Subscript(self, node):
        raise ExpressionError("Subscript forbidden")
    def collect(self, tree: ast.AST) -> set[str]:
        self.visit(tree); return self.names


@dataclass
class TypedExpression:
    source: str
    tree: ast.Expression
    result_unit: Unit
    free_names: frozenset[str]

    def evaluate(self, ctx: Dict[str, float]) -> Any:
        return _Evaluator(ctx).visit(self.tree)


def parse_and_type(source: str, name_units: Dict[str, Unit]) -> TypedExpression:
    for tok in FORBIDDEN:
        if tok in source:
            raise ExpressionError(f"Forbidden token in '{source}': {tok}")
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as e:
        raise ExpressionError(f"Syntax error in '{source}': {e}") from e
    names = _NameCollector().collect(tree)
    result_unit = _TypeChecker(name_units).visit(tree.body)
    if result_unit is None:
        result_unit = Unit("bool", BOOLEAN)
    return TypedExpression(source=source, tree=tree, result_unit=result_unit,
                           free_names=frozenset(names))


def parse_untyped(source: str) -> TypedExpression:
    for tok in FORBIDDEN:
        if tok in source:
            raise ExpressionError(f"Forbidden token: {tok}")
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as e:
        raise ExpressionError(f"Syntax error: {e}")
    names = _NameCollector().collect(tree)
    return TypedExpression(
        source=source, tree=tree,
        result_unit=Unit("1", DIMENSIONLESS),
        free_names=frozenset(names))


class _TypeChecker(ast.NodeVisitor):
    def __init__(self, name_units: Dict[str, Unit]):
        self.name_units = name_units

    def visit_Constant(self, node) -> Unit:
        if isinstance(node.value, bool):
            return Unit("bool", BOOLEAN)
        if isinstance(node.value, (int, float)):
            return Unit("1", DIMENSIONLESS)
        raise ExpressionError(f"Unsupported constant: {type(node.value).__name__}")

    def visit_Name(self, node) -> Unit:
        if node.id not in self.name_units:
            raise ExpressionError(f"Unknown name: {node.id}")
        return self.name_units[node.id]

    def visit_BinOp(self, node) -> Unit:
        if type(node.op) not in BINOPS:
            raise ExpressionError(f"Unsupported op: {type(node.op).__name__}")
        _, _, kind = BINOPS[type(node.op)]
        l_unit = self.visit(node.left)
        r_unit = self.visit(node.right)
        if kind == "add":
            return check_additive_compat(l_unit, r_unit, BINOPS[type(node.op)][0])
        if kind == "mul":
            new_dim = l_unit.dimension * r_unit.dimension
            return Unit(f"({l_unit.name}*{r_unit.name})", new_dim,
                        l_unit.scale * r_unit.scale)
        if kind == "div":
            new_dim = l_unit.dimension / r_unit.dimension
            return Unit(f"({l_unit.name}/{r_unit.name})", new_dim,
                        l_unit.scale / r_unit.scale if r_unit.scale else 1.0)
        if kind == "pow":
            if not isinstance(node.right, ast.Constant) or not isinstance(node.right.value, int):
                raise ExpressionError("Power exponent must be an integer literal")
            n = node.right.value
            return Unit(f"({l_unit.name}^{n})", l_unit.dimension ** n, l_unit.scale ** n)
        if kind == "mod":
            return check_additive_compat(l_unit, r_unit, "%")
        raise ExpressionError(f"Unhandled binop: {kind}")

    def visit_UnaryOp(self, node) -> Unit:
        if type(node.op) not in UNARYOPS:
            raise ExpressionError(f"Unsupported unary: {type(node.op).__name__}")
        inner = self.visit(node.operand)
        if isinstance(node.op, ast.Not):
            return Unit("bool", BOOLEAN)
        return inner

    def visit_BoolOp(self, node) -> Unit:
        for v in node.values:
            self.visit(v)
        return Unit("bool", BOOLEAN)

    def visit_Compare(self, node) -> Unit:
        """
        Comparisons are valid if:
        1. Both sides have the same dimension (e.g. V == V)
        2. One side is dimensionless (e.g. V > 100.0) — allows threshold literals
        """
        left = self.visit(node.left)
        for op, comp in zip(node.ops, node.comparators):
            right = self.visit(comp)
            
            # Allow comparison if either side is dimensionless (literal)
            # or if both sides have the exact same dimension
            if not (left.dimension.is_dimensionless() or 
                    right.dimension.is_dimensionless() or 
                    left.dimension == right.dimension):
                raise DimensionError(
                    f"Cannot compare {left.name} with {right.name}: incompatible dimensions")
            left = right
        return Unit("bool", BOOLEAN)

    def visit_Call(self, node) -> Unit:
        if not isinstance(node.func, ast.Name):
            raise ExpressionError("Only simple function calls allowed")
        name = node.func.id
        if name not in FUNCTIONS:
            raise ExpressionError(f"Unknown function: {name}")
        _, arity = FUNCTIONS[name]
        if len(node.args) != arity:
            raise ExpressionError(f"{name} expects {arity} args")
        arg_units = [self.visit(a) for a in node.args]
        if name in ("sin", "cos", "exp", "log"):
            if not arg_units[0].dimension.is_dimensionless():
                raise DimensionError(f"{name}() requires dimensionless argument")
            return Unit("1", DIMENSIONLESS)
        if name == "sqrt":
            new_dim = Dimension(tuple(e // 2 for e in arg_units[0].dimension.vec))
            return Unit(f"sqrt({arg_units[0].name})", new_dim)
        if name == "abs":
            return arg_units[0]
        if name in ("min", "max"):
            return check_additive_compat(arg_units[0], arg_units[1], name)
        if name == "pow":
            if not isinstance(node.args[1], ast.Constant):
                raise ExpressionError("pow exponent must be literal")
            n = int(node.args[1].value)
            return Unit(f"pow({arg_units[0].name},{n})", arg_units[0].dimension ** n)
        return Unit("1", DIMENSIONLESS)

    def visit_IfExp(self, node) -> Unit:
        self.visit(node.test)
        t_unit = self.visit(node.body)
        f_unit = self.visit(node.orelse)
        return check_additive_compat(t_unit, f_unit, "ternary")

    def generic_visit(self, node) -> Unit:
        raise ExpressionError(f"Unsupported node: {type(node).__name__}")


class _Evaluator(ast.NodeVisitor):
    def __init__(self, ctx: Dict[str, Any]):
        self.ctx = ctx

    def visit_Expression(self, node): return self.visit(node.body)

    def visit_Constant(self, node):
        if isinstance(node.value, (int, float, bool)):
            return node.value
        raise ExpressionError(f"Unsupported constant")

    def visit_Name(self, node):
        if node.id not in self.ctx:
            raise ExpressionError(f"Unknown name: {node.id}")
        return self.ctx[node.id]

    def visit_BinOp(self, node):
        _, fn, _ = BINOPS[type(node.op)]
        return fn(self.visit(node.left), self.visit(node.right))

    def visit_UnaryOp(self, node):
        _, fn = UNARYOPS[type(node.op)]
        return fn(self.visit(node.operand))

    def visit_BoolOp(self, node):
        if isinstance(node.op, ast.And):
            return all(self.visit(v) for v in node.values)
        return any(self.visit(v) for v in node.values)

    def visit_Compare(self, node):
        left = self.visit(node.left)
        for op, comp in zip(node.ops, node.comparators):
            _, fn = CMPOPS[type(op)]
            right = self.visit(comp)
            if not fn(left, right):
                return False
            left = right
        return True

    def visit_Call(self, node):
        name = node.func.id
        fn, _ = FUNCTIONS[name]
        return fn(*[self.visit(a) for a in node.args])

    def visit_IfExp(self, node):
        return self.visit(node.body) if self.visit(node.test) else self.visit(node.orelse)

    def generic_visit(self, node):
        raise ExpressionError(f"Unsupported node: {type(node).__name__}")


