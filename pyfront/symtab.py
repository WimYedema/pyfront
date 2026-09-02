from typing import Self

from pyfront.lang.model import Front, ReferenceSymbol, Rule
from pyfront.lang.walk import walk_front


class SymbolTable:
    def __init__(self, front: Front):
        self.front = front
        self.adding = True
        self.symbols = {
            "Ident": None,
            "Int": None,
            "String": None,
            "Float": None,
        }

    def add_symbol(self, name: str, symbol) -> None:
        if self.adding:
            if name in self.symbols:
                raise ValueError(f"Duplicate symbol name: {name}")
            self.symbols[name] = symbol

    def get_symbol[T](self, name: str, type: type[T]) -> T:
        symbol = self.symbols.get(name)
        if symbol is not None and not isinstance(symbol, type):
            raise ValueError(f"Symbol '{name}' is not of type {type.__name__}.")
        return symbol

    def pre_rule(self, rule: Rule) -> None:
        self.add_symbol(rule.name, rule)

    def pre_reference_symbol(self, symbol: ReferenceSymbol) -> None:
        symbol.rule = self.get_symbol(symbol.name, Rule)

    @classmethod
    def populate(cls, front: Front) -> Self:
        symbol_table = cls(front)
        walk_front(front, symbol_table)
        symbol_table.adding = False
        walk_front(front, symbol_table)
        return symbol_table
