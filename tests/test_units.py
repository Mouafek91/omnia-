import pytest
from nexforge.compiler.units import lookup_unit, DimensionError, check_additive_compat
from nexforge.compiler.expr import parse_and_type


def test_add_same_unit():
    v = lookup_unit("V")
    result = check_additive_compat(v, v, "+")
    assert result == v


def test_add_different_units_fails():
    v = lookup_unit("V")
    c = lookup_unit("degC")
    with pytest.raises(DimensionError):
        check_additive_compat(v, c, "+")


def test_multiply_units():
    ctx = {"v": lookup_unit("V"), "i": lookup_unit("A")}
    expr = parse_and_type("v * i", ctx)
    expected = lookup_unit("V").dimension * lookup_unit("A").dimension
    assert expr.result_unit.dimension == expected


def test_sin_requires_dimensionless():
    ctx = {"v": lookup_unit("V")}
    with pytest.raises(DimensionError):
        parse_and_type("sin(v)", ctx)


def test_evaluate_arithmetic():
    ctx = {"x": lookup_unit("V"), "y": lookup_unit("V")}
    expr = parse_and_type("x * 2 + y", ctx)
    assert expr.evaluate({"x": 10.0, "y": 5.0}) == 25.0
