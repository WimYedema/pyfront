from dataclasses import dataclass


@dataclass
class Symbol:
    pass


@dataclass
class SymbolSequence:
    symbols: list[Symbol]
    type: list[str] | None = None


@dataclass
class LabeledSymbol(Symbol):
    label: str
    symbol: Symbol


@dataclass
class StringSymbol(Symbol):
    value: str


@dataclass
class SeparatedSymbol(Symbol):
    symbol: Symbol
    separator: str


@dataclass
class KeywordSymbol(Symbol):
    keyword: str
    rule: Rule | None = None


@dataclass
class GroupSymbol(Symbol):
    symbols: SymbolSequence
    optional: bool = False
    multiple: bool = False


@dataclass
class Expression:
    pass


@dataclass
class IdExpr(Expression):
    id: str


@dataclass
class StringExpr(Expression):
    value: str


@dataclass
class IntExpr(Expression):
    value: int


@dataclass
class FloatExpr(Expression):
    value: float


@dataclass
class TrueExpr(Expression):
    pass


@dataclass
class FalseExpr(Expression):
    pass


@dataclass
class NoneExpr(Expression):
    pass


@dataclass
class Field:
    name: str
    type: Symbol
    value: Expression | None


@dataclass
class Rule:
    is_root: bool
    name: str
    super_type: str | None
    fields: list[Field]
    terms: SymbolSequence
    alts: list[Rule] | None
    post_terms: SymbolSequence | None

    is_ref: bool = False
    super_rule: Rule | None = None


@dataclass
class Front:
    rules: list[Rule]
