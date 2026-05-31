"""Python → C++ expression transpiler using AST."""
from __future__ import annotations
import ast


class TranspilerError(Exception):
    pass


class _Py2CPP(ast.NodeVisitor):
    BINOP = {
        ast.Add: "+", ast.Sub: "-", ast.Mult: "*",
        ast.Div: "/", ast.Mod: "%", ast.FloorDiv: "/",
    }
    CMP = {
        ast.Eq: "==", ast.NotEq: "!=",
        ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
    }
    UNARY = {ast.UAdd: "+", ast.USub: "-", ast.Not: "!", ast.Invert: "~"}
    BOOL = {ast.And: "&&", ast.Or: "||"}
    FUNCS = {"abs", "sqrt", "sin", "cos", "exp", "log", "pow", "min", "max"}

    def transpile(self, expr: str) -> str:
        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as e:
            raise TranspilerError(f"Invalid: {e}")
        return self.visit(tree.body)

    def visit(self, n):
        return getattr(self, f"visit_{type(n).__name__}", self._bad)(n)

    def _bad(self, n):
        raise TranspilerError(f"Unsupported: {type(n).__name__}")

    def visit_BoolOp(self, n):
        op = self.BOOL[type(n.op)]
        return "(" + f" {op} ".join(self.visit(v) for v in n.values) + ")"

    def visit_BinOp(self, n):
        if isinstance(n.op, ast.Pow):
            return f"pow({self.visit(n.left)}, {self.visit(n.right)})"
        op = self.BINOP.get(type(n.op))
        if op is None:
            raise TranspilerError(f"Bad op: {type(n.op).__name__}")
        return f"({self.visit(n.left)} {op} {self.visit(n.right)})"

    def visit_UnaryOp(self, n):
        op = self.UNARY.get(type(n.op))
        if op is None:
            raise TranspilerError(f"Bad unary: {type(n.op).__name__}")
        return f"{op}({self.visit(n.operand)})"

    def visit_Compare(self, n):
        left = self.visit(n.left)
        parts = []
        for op, c in zip(n.ops, n.comparators):
            if type(op) not in self.CMP:
                raise TranspilerError(f"Bad cmp: {type(op).__name__}")
            right = self.visit(c)
            parts.append(f"({left} {self.CMP[type(op)]} {right})")
            left = right
        return " && ".join(parts) if len(parts) > 1 else parts[0]

    def visit_Name(self, n):
        if n.id.startswith("_"):
            raise TranspilerError(f"Private: {n.id}")
        return n.id

    def visit_Constant(self, n):
        if isinstance(n.value, bool):
            return "true" if n.value else "false"
        if isinstance(n.value, (int, float)):
            s = str(n.value)
            if isinstance(n.value, float) and "." not in s and "e" not in s.lower():
                s += ".0"
            return s
        raise TranspilerError(f"Bad const: {type(n.value).__name__}")

    def visit_Call(self, n):
        if not isinstance(n.func, ast.Name):
            raise TranspilerError("Only simple calls")
        if n.func.id not in self.FUNCS:
            raise TranspilerError(f"Forbidden func: {n.func.id}")
        args = ", ".join(self.visit(a) for a in n.args)
        if n.func.id in ("min", "max"):
            return f"std::{n.func.id}({args})"
        return f"{n.func.id}({args})"

    def visit_IfExp(self, n):
        return (f"({self.visit(n.test)} ? "
                f"{self.visit(n.body)} : {self.visit(n.orelse)})")


def python_to_cpp(expr: str) -> str:
    return _Py2CPP().transpile(expr)
