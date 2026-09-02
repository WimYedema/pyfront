import pyfront.lang.model as lang


def gen_expression(expr: lang.Expression) -> str:
    """Generate a string representation of the given expression."""
    match expr:
        case lang.IdExpr(id=id):
            return f'"{id}"'
        case lang.StringExpr(value=value):
            return f'"{value}"'
        case lang.IntExpr(value=value):
            return str(value)
        case lang.FloatExpr(value=value):
            return str(value)
        case lang.TrueExpr():
            return "True"
        case lang.FalseExpr():
            return "False"
        case lang.NoneExpr():
            return "None"
        case _:
            raise ValueError(f"Unknown expression: {expr}")
