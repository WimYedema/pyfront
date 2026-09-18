from typing import Self

from pyfront.lang.model import Front, ReferenceSymbol, Rule, ScanRule
from pyfront.lang.walk import walk_front


class SymbolTable:
    def __init__(self, front: Front):
        self.front = front
        self.adding = True
        self.symbols = {
            "Ident": ScanRule(name="Ident", type="Ident", pattern=r"[a-zA-Z_][a-zA-Z0-9_]*"),
            "Int": ScanRule(name="Int", type="Int", pattern=r"[0-9]+"),
            "String": ScanRule(
                name="String",
                type="String",
                pattern=r"""r'\"(?P<value>[^"]*)\"'""",
                format='"{value}"',
            ),
            "Float": ScanRule(name="Float", type="Float", pattern=r"[0-9]+\.[0-9]+"),
        }

    def add_symbol(self, name: str, symbol: object) -> None:
        if self.adding:
            if name in self.symbols:
                raise ValueError(f"Duplicate symbol name: {name}")
            self.symbols[name] = symbol

    def get_symbol[T](self, name: str, *types: type[T]) -> T:
        symbol = self.symbols.get(name)
        if symbol is not None and not isinstance(symbol, types):
            raise ValueError(f"Symbol '{name}' is not of type {types}.")
        return symbol

    def pre_rule(self, rule: Rule) -> None:
        self.add_symbol(rule.name, rule)

    def pre_scan_rule(self, rule: ScanRule) -> None:
        self.add_symbol(rule.name, rule)

    def pre_reference_symbol(self, symbol: ReferenceSymbol) -> None:
        symbol.rule = self.get_symbol(symbol.name, Rule, ScanRule)

    @classmethod
    def populate(cls, front: Front) -> Self:
        symbol_table = cls(front)
        walk_front(front, symbol_table)
        symbol_table.adding = False
        walk_front(front, symbol_table)
        return symbol_table
