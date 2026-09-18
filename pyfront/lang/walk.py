from collections.abc import Generator, Iterable
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field, fields
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

WalkT = TypeVar("WalkT")


@dataclass
class Walk:
    class Down:
        """propagate this field down in the AST."""

    _stack: list[dict[str, object]] = field(init=False, repr=False, hash=False, compare=False)

    def __post_init__(self):
        self._stack = []

    def _go_down_(self):
        entry = {}
        for fld in fields(self):
            if hasattr(fld.type, "__metadata__") and Walk.Down in fld.type.__metadata__:
                entry[fld.name] = getattr(self, fld.name)
        self._stack.append(entry)

    def _go_up_(self):
        for k, v in self._stack.pop().items():
            setattr(self, k, v)


def _invoke_walk_method[WalkT](walk: WalkT, method_name: str, *args: Any) -> None:
    """Invoke a method on the Walk object if it exists."""
    method = getattr(walk, method_name, None)
    if callable(method):
        method(*args)


@contextmanager
def _into_one[WalkT](type_name: str, walk: WalkT, *args: Any) -> Generator[None]:
    """Context manager to invoke a method on the Walk object."""
    if hasattr(walk, "_go_down_"):
        walk._go_down_()

    _invoke_walk_method(walk, "pre_" + type_name, *args)

    method = getattr(walk, "into_" + type_name, None)
    if callable(method):
        yield from method(*args)
    else:
        yield

    _invoke_walk_method(walk, "post_" + type_name, *args)

    if hasattr(walk, "_go_up_"):
        walk._go_up_()


@contextmanager
def _into[WalkT](type_name: str, walks: Iterable[WalkT], *args: Any) -> Generator[None]:
    """Context manager to invoke a method on the Walk object."""
    with ExitStack() as stack:
        for walk in walks:
            stack.enter_context(_into_one(type_name, walk, *args))
        yield


def walk_symbol[WalkT](symbol: Symbol, *walks: WalkT) -> None:
    """Walk through a Symbol object."""
    with _into("symbol", walks, symbol):
        match symbol:
            case LabeledSymbol(label=_, symbol=inner_symbol):
                with _into("labeled_symbol", walks, symbol):
                    walk_symbol(inner_symbol, *walks)
            case StringSymbol(value=_):
                with _into("string_symbol", walks, symbol):
                    pass  # No further action needed for StringSymbol
            case SeparatedSymbol(symbol=inner_symbol, separator=separator):
                with _into("separated_symbol", walks, symbol):
                    walk_symbol(inner_symbol, *walks)
                    walk_symbol(separator, *walks)
            case ReferenceSymbol(name=_):
                with _into("reference_symbol", walks, symbol):
                    pass  # No further action needed for KeywordSymbol
            case OptionalSymbol(symbols=symbols):
                with _into("optional_symbol", walks, symbol):
                    walk_symbol_sequence(symbols, *walks)
            case MoreSymbol(symbols=symbols, optional=_):
                with _into("more_symbol", walks, symbol):
                    walk_symbol_sequence(symbols, *walks)
            case GroupSymbol(symbols=symbols):
                with _into("group_symbol", walks, symbol):
                    walk_symbol_sequence(symbols, *walks)


def walk_symbol_sequence[WalkT](symbol_sequence: SymbolSequence, *walks: WalkT) -> None:
    """Walk through a SymbolSequence object."""
    with _into("symbol_sequence", walks, symbol_sequence):
        for sym in symbol_sequence.symbols:
            walk_symbol(sym, *walks)


def walk_expression[WalkT](expr, *walks: WalkT) -> None:
    """Walk through an Expression object."""
    with _into("expression", walks, expr):
        match expr:
            case IdExpr(id=_):
                with _into("id_expr", walks, expr):
                    pass  # No further action needed for IdExpr
            case StringExpr(value=_):
                with _into("string_expr", walks, expr):
                    pass  # No further action needed for StringExpr
            case IntExpr(value=_):
                with _into("int_expr", walks, expr):
                    pass  # No further action needed for IntExpr
            case FloatExpr(value=_):
                with _into("float_expr", walks, expr):
                    pass  # No further action needed for FloatExpr
            case TrueExpr():
                with _into("true_expr", walks, expr):
                    pass  # No further action needed for TrueExpr
            case FalseExpr():
                with _into("false_expr", walks, expr):
                    pass  # No further action needed for FalseExpr
            case NoneExpr():
                with _into("none_expr", walks, expr):
                    pass  # No further action needed for NoneExpr


def walk_field[WalkT](field, *walks: WalkT) -> None:
    """Walk through a Field object."""
    with _into("field", walks, field):
        walk_symbol(field.type, *walks)
        if field.value is not None:
            walk_expression(field.value, *walks)


def walk_choice[WalkT](choice, *walks: WalkT) -> None:
    """Walk through a Choice object."""
    with _into("choice", walks, choice):
        match choice:
            case RuleChoice(rule=rule):
                with _into("rule_choice", walks, choice):
                    walk_rule_base(rule, *walks)
            case SymbolsChoice(symbols=symbols):
                with _into("symbols_choice", walks, choice):
                    walk_symbol_sequence(symbols, *walks)


def walk_rule_base[WalkT](rule, *walks: WalkT) -> None:
    """Walk through a Rule object."""
    with _into("rule_base", walks, rule):
        match rule:
            case Rule(terms=terms, choices=choices):
                with _into("rule", walks, rule):
                    for field in rule.fields:
                        walk_field(field, *walks)
                    walk_symbol_sequence(terms, *walks)
                    for choice in choices or []:
                        walk_choice(choice, *walks)


def walk_front[WalkT](front: Front, *walks: WalkT) -> None:
    """Walk through a Front object."""
    with _into("front", walks, front):
        for rule in front.rules:
            walk_rule_base(rule, *walks)
