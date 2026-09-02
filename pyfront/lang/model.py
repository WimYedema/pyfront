from dataclasses import dataclass


@dataclass
class Symbol:
    pass


@dataclass
class SymbolSequence:
    symbols: list[Symbol]
    type: list[str] | None = None

    def __str__(self) -> str:
        return " ".join(str(symbol) for symbol in self.symbols)


@dataclass
class LabeledSymbol(Symbol):
    label: str
    symbol: Symbol

    def __str__(self) -> str:
        return f"{self.label}: {self.symbol}"


@dataclass
class StringSymbol(Symbol):
    value: str

    def __str__(self) -> str:
        return f"{self.value}"


@dataclass
class SeparatedSymbol(Symbol):
    symbol: Symbol
    separator: str

    def __str__(self) -> str:
        return f'{self.symbol} / "{self.separator}"'


@dataclass
class KeywordSymbol(Symbol):
    keyword: str
    rule: Rule | None = None

    def __str__(self) -> str:
        return self.keyword


@dataclass
class GroupSymbol(Symbol):
    symbols: SymbolSequence
    optional: bool = False
    multiple: bool = False

    def __str__(self) -> str:
        if self.multiple:
            return f"{{ {self.symbols} }}{'' if self.optional else '+'}"
        elif self.optional:
            return f"[ {self.symbols} ]"
        else:
            return f"( {self.symbols} )"


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

    is_ref: bool = False
    super_rule: Rule | None = None

    def __str__(self) -> str:
        if self.is_ref:
            return self.name
        terms_str = " ".join(str(term) for term in self.terms.symbols)
        if not self.alts:
            return f"{self.name} ::= {terms_str}"
        else:
            alts_str = " | ".join(str(alt) for alt in self.alts)
            return f"{self.name} ::= {terms_str} < {alts_str} >"


@dataclass
class ScanRule:
    name: str
    type: str
    pattern: str

    def __str__(self) -> str:
        return f"SCAN {self.name} : {self.type} ::= {self.pattern}"


@dataclass
class Front:
    rules: list[Rule]
    scan_rules: list[ScanRule]
