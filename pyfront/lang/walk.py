from collections.abc import Iterable
from contextlib import contextmanager
from typing import Any, TypeVar

from .model import (
    FalseExpr,
    FloatExpr,
    Front,
    GroupSymbol,
    IdExpr,
    IntExpr,
    LabeledSymbol,
    MoreSymbol,
    NoneExpr,
    OptionalSymbol,
    ReferenceSymbol,
    Rule,
    RuleChoice,
    SeparatedSymbol,
    StringExpr,
    StringSymbol,
    Symbol,
    SymbolsChoice,
    SymbolSequence,
    TrueExpr,
)

Walk = TypeVar("Walk")


def _invoke_walk_method[Walk](walk: Walk, method_name: str, *args: Any) -> None:
    """Invoke a method on the Walk object if it exists."""
    method = getattr(walk, method_name, None)
    if callable(method):
        method(*args)


@contextmanager
def _into[Walk](type_name: str, walk: Walk, *args: Any) -> Iterable[None]:
    """Context manager to invoke a method on the Walk object."""
    _invoke_walk_method(walk, "pre_" + type_name, *args)
    method = getattr(walk, "into_" + type_name, None)
    if callable(method):
        yield from method(*args)
    else:
        yield
    _invoke_walk_method(walk, "post_" + type_name, *args)


def walk_symbol[Walk](symbol: Symbol, walk: Walk) -> Walk:
    """Walk through a Symbol object."""
    with _into("symbol", walk, symbol):
        match symbol:
            case LabeledSymbol(label=_, symbol=inner_symbol):
                with _into("labeled_symbol", walk, symbol):
                    walk_symbol(inner_symbol, walk)
            case StringSymbol(value=_):
                with _into("string_symbol", walk, symbol):
                    pass  # No further action needed for StringSymbol
            case SeparatedSymbol(symbol=inner_symbol, separator=separator):
                with _into("separated_symbol", walk, symbol):
                    walk_symbol(inner_symbol, walk)
                    walk_symbol(separator, walk)
            case ReferenceSymbol(name=_):
                with _into("reference_symbol", walk, symbol):
                    pass  # No further action needed for KeywordSymbol
            case OptionalSymbol(symbols=symbols):
                with _into("optional_symbol", walk, symbol):
                    walk_symbol_sequence(symbols, walk)
            case MoreSymbol(symbols=symbols, optional=_):
                with _into("more_symbol", walk, symbol):
                    walk_symbol_sequence(symbols, walk)
            case GroupSymbol(symbols=symbols):
                with _into("group_symbol", walk, symbol):
                    walk_symbol_sequence(symbols, walk)
    return walk


def walk_symbol_sequence[Walk](symbol_sequence: SymbolSequence, walk: Walk) -> Walk:
    """Walk through a SymbolSequence object."""
    with _into("symbol_sequence", walk, symbol_sequence):
        for sym in symbol_sequence.symbols:
            walk_symbol(sym, walk)
    return walk


def walk_expression[Walk](expr, walk: Walk) -> Walk:
    """Walk through an Expression object."""
    with _into("expression", walk, expr):
        match expr:
            case IdExpr(id=_):
                with _into("id_expr", walk, expr):
                    pass  # No further action needed for IdExpr
            case StringExpr(value=_):
                with _into("string_expr", walk, expr):
                    pass  # No further action needed for StringExpr
            case IntExpr(value=_):
                with _into("int_expr", walk, expr):
                    pass  # No further action needed for IntExpr
            case FloatExpr(value=_):
                with _into("float_expr", walk, expr):
                    pass  # No further action needed for FloatExpr
            case TrueExpr():
                with _into("true_expr", walk, expr):
                    pass  # No further action needed for TrueExpr
            case FalseExpr():
                with _into("false_expr", walk, expr):
                    pass  # No further action needed for FalseExpr
            case NoneExpr():
                with _into("none_expr", walk, expr):
                    pass  # No further action needed for NoneExpr
    return walk


def walk_field[Walk](field, walk: Walk) -> Walk:
    """Walk through a Field object."""
    with _into("field", walk, field):
        walk_symbol(field.type, walk)
        if field.value is not None:
            walk_expression(field.value, walk)
    return walk


def walk_choice[Walk](choice, walk: Walk) -> Walk:
    """Walk through a Choice object."""
    with _into("choice", walk, choice):
        match choice:
            case RuleChoice(rule=rule):
                with _into("rule_choice", walk, choice):
                    walk_rule_base(rule, walk)
            case SymbolsChoice(symbols=symbols):
                with _into("symbols_choice", walk, choice):
                    walk_symbol_sequence(symbols, walk)
    return walk


def walk_rule_base[Walk](rule, walk: Walk) -> Walk:
    """Walk through a Rule object."""
    with _into("rule_base", walk, rule):
        match rule:
            case Rule(terms=terms, choices=choices):
                with _into("rule", walk, rule):
                    for field in rule.fields:
                        walk_field(field, walk)
                    walk_symbol_sequence(terms, walk)
                    for choice in choices or []:
                        walk_choice(choice, walk)
    return walk


def walk_front[Walk](front: Front, walk: Walk) -> Walk:
    """Walk through a Front object."""
    with _into("front", walk, front):
        for rule in front.rules:
            walk_rule_base(rule, walk)
    return walk
