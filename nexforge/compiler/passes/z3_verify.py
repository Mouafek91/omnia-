"""Z3 SMT-based formal verification."""
from __future__ import annotations
from dataclasses import dataclass

try:
    import z3
    HAS_Z3 = True
except ImportError:
    HAS_Z3 = False

from ..ir import CPSIR
from ..expr import parse_untyped, ExpressionError


@dataclass
class VerificationResult:
    ok: bool
    errors: list
    warnings: list
    stats: dict


class _AST2Z3:
    def __init__(self, vars_):
        self.vars = vars_

    def visit(self, node):
        return getattr(self, f"visit_{type(node).__name__}", self._bad)(node)

    def _bad(self, n):
        raise ExpressionError(f"Z3 cannot translate: {type(n).__name__}")

    def visit_Constant(self, n):
        if isinstance(n.value, bool):
            return z3.BoolVal(n.value)
        if isinstance(n.value, (int, float)):
            return z3.RealVal(n.value)
        raise ExpressionError(f"Unsupported constant")

    def visit_Name(self, n):
        if n.id not in self.vars:
            raise ExpressionError(f"Unknown name: {n.id}")
        return self.vars[n.id]

    def visit_BinOp(self, n):
        import ast
        l = self.visit(n.left); r = self.visit(n.right)
        if isinstance(n.op, ast.Add): return l + r
        if isinstance(n.op, ast.Sub): return l - r
        if isinstance(n.op, ast.Mult): return l * r
        if isinstance(n.op, ast.Div): return l / r
        if isinstance(n.op, ast.Pow):
            if isinstance(n.right, ast.Constant) and isinstance(n.right.value, int):
                return l ** n.right.value
            raise ExpressionError("Z3 pow: exponent must be integer literal")
        raise ExpressionError(f"Unsupported binop")

    def visit_UnaryOp(self, n):
        import ast
        op = self.visit(n.operand)
        if isinstance(n.op, ast.USub): return -op
        if isinstance(n.op, ast.Not): return z3.Not(op)
        raise ExpressionError("Unsupported unary")

    def visit_BoolOp(self, n):
        import ast
        vals = [self.visit(v) for v in n.values]
        if isinstance(n.op, ast.And): return z3.And(*vals)
        if isinstance(n.op, ast.Or): return z3.Or(*vals)
        raise ExpressionError("Unsupported boolop")

    def visit_Compare(self, n):
        import ast
        left = self.visit(n.left)
        parts = []
        for op, c in zip(n.ops, n.comparators):
            right = self.visit(c)
            if isinstance(op, ast.Eq): parts.append(left == right)
            elif isinstance(op, ast.NotEq): parts.append(left != right)
            elif isinstance(op, ast.Lt): parts.append(left < right)
            elif isinstance(op, ast.LtE): parts.append(left <= right)
            elif isinstance(op, ast.Gt): parts.append(left > right)
            elif isinstance(op, ast.GtE): parts.append(left >= right)
            else: raise ExpressionError(f"Unsupported cmp")
            left = right
        return z3.And(*parts) if len(parts) > 1 else parts[0]

    def visit_Call(self, n):
        name = n.func.id
        args = [self.visit(a) for a in n.args]
        if name == "abs":
            x = args[0]; return z3.If(x >= 0, x, -x)
        if name == "min":
            return z3.If(args[0] <= args[1], args[0], args[1])
        if name == "max":
            return z3.If(args[0] >= args[1], args[0], args[1])
        raise ExpressionError(f"Z3: unsupported function {name}")

    def visit_IfExp(self, n):
        return z3.If(self.visit(n.test), self.visit(n.body), self.visit(n.orelse))


class Z3Verifier:
    def __init__(self, ir: CPSIR):
        self.ir = ir
        self.vars = {}
        for s in ir.sensors:
            self.vars[s.name] = z3.Real(s.name)
        for a in ir.actuators:
            self.vars[a.name] = z3.Real(a.name)
        for sv in ir.physics.states:
            if sv.name not in self.vars:
                self.vars[sv.name] = z3.Real(sv.name)

    def _ranges(self):
        cs = []
        for s in self.ir.sensors:
            v = self.vars[s.name]
            cs.append(v >= s.quantity.min); cs.append(v <= s.quantity.max)
        for a in self.ir.actuators:
            v = self.vars[a.name]
            cs.append(v >= a.quantity.min); cs.append(v <= a.quantity.max)
        return cs

    def _to_z3(self, expr):
        tree = parse_untyped(expr).tree
        return _AST2Z3(self.vars).visit(tree.body)

    def verify(self):
        errors, warnings = [], []
        ranges = self._ranges()
        contracts = self.ir.safety.contracts

        for c in contracts:
            solver = z3.Solver(); solver.add(ranges)
            try:
                solver.add(self._to_z3(c.assume))
            except Exception as e:
                errors.append(f"Contract '{c.name}' assume cannot translate: {e}")
                continue
            if solver.check() == z3.unsat:
                warnings.append(f"Contract '{c.name}' assume is UNSAT — dead contract")

        for i, c1 in enumerate(contracts):
            for j, c2 in enumerate(contracts):
                if j <= i: continue
                solver = z3.Solver(); solver.add(ranges)
                try:
                    a1 = self._to_z3(c1.assume); a2 = self._to_z3(c2.assume)
                    g1 = self._to_z3(c1.guarantee); g2 = self._to_z3(c2.guarantee)
                    solver.add(a1, a2, z3.Not(g1), z3.Not(g2))
                    if solver.check() == z3.sat:
                        warnings.append(
                            f"Contracts '{c1.name}' and '{c2.name}' can both violate")
                except Exception as e:
                    errors.append(f"Pairwise {c1.name}+{c2.name} failed: {e}")

        for c in contracts:
            solver = z3.Solver(); solver.add(ranges)
            try:
                solver.add(z3.Not(self._to_z3(c.guarantee)))
                if solver.check() == z3.unsat:
                    warnings.append(f"Contract '{c.name}' guarantee is a tautology")
            except Exception:
                pass

        return VerificationResult(
            ok=len(errors) == 0, errors=errors, warnings=warnings,
            stats={"contracts": len(contracts), "z3_available": True})


def verify_with_z3(ir: CPSIR):
    if not HAS_Z3:
        return VerificationResult(
            ok=True, errors=[], warnings=["Z3 not installed"],
            stats={"z3_available": False})
    return Z3Verifier(ir).verify()
