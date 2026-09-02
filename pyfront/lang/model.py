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
class ReferenceSymbol(Symbol):
    name: str
    rule: Rule | None = None

    def __str__(self) -> str:
        return self.name


@dataclass
class GroupSymbol(Symbol):
    symbols: SymbolSequence

    def __str__(self) -> str:
        return f"( {self.symbols} )"


@dataclass
class OptionalSymbol(Symbol):
    symbols: SymbolSequence

    def __str__(self) -> str:
        return f"[ {self.symbols} ]"


@dataclass
class MoreSymbol(Symbol):
    symbols: SymbolSequence
    optional: bool = False

    def __str__(self) -> str:
        return f"{{ {self.symbols} }}{'' if self.optional else '+'}"


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
class Choice:
    pass


@dataclass
class RuleChoice(Choice):
    rule: Rule

    def __str__(self) -> str:
        return str(self.rule)


@dataclass
class SymbolsChoice(Choice):
    symbols: SymbolSequence

    def __str__(self) -> str:
        return str(self.symbols)


@dataclass
class Rule:
    is_root: bool
    name: str
    super_type: str | None
    fields: list[Field]
    terms: SymbolSequence
    choices: list[Choice] | None

    def __str__(self) -> str:
        terms_str = " ".join(str(term) for term in self.terms.symbols)
        if not self.choices:
            return f"{self.name} ::= {terms_str}"
        else:
            choices_str = " | ".join(str(choice) for choice in self.choices)
            return f"{self.name} ::= {terms_str} < {choices_str} >"


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
