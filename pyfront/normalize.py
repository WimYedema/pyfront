from pyfront.lang.model import (
    Front,
    GroupSymbol,
    KeywordSymbol,
    LabeledSymbol,
    Rule,
    SeparatedSymbol,
    StringSymbol,
    SymbolSequence,
)
from pyfront.lang.walk import walk_front


class Normalize:
    def __init__(self, front: Front) -> None:
        self.front = front
        self.current_label: list[str] = []
        self.current_rule: Rule | None = None

    def pre_rule(self, rule: Rule) -> None:
        self.current_rule = rule
        # new_rules = []
        # for alt in rule.alts or []:
        #     if not alt.is_ref:
        #         alt.super_type = self.current_rule.name
        #         alt.super_rule = self.current_rule

        #         self.front.rules.append(alt)
        #         new_rules.append(
        #             Rule(
        #                 is_root=False,
        #                 name=alt.name,
        #                 super_type=None,
        #                 fields=[],
        #                 terms=SymbolSequence(symbols=[]),
        #                 is_ref=True,
        #             )
        #         )
        #     else:
        #         new_rules.append(alt)

        # rule.alts = new_rules

    def pre_labeled_symbol(self, symbol: LabeledSymbol) -> None:
        self.current_label.append(symbol.label)

    def post_labeled_symbol(self, symbol: LabeledSymbol) -> None:
        self.current_label.pop()
        symbol.type = symbol.symbol.type

    def post_keyword_symbol(self, symbol: KeywordSymbol) -> None:
        sym_type = symbol.keyword
        match sym_type:
            case "Ident":
                sym_type = "str"
            case "Int":
                sym_type = "int"
            case "Float":
                sym_type = "float"
            case "String":
                sym_type = "str"
            case "Bool":
                sym_type = "bool"
        symbol.type = [sym_type]

    def post_string_symbol(self, symbol: StringSymbol) -> None:
        symbol.type = []

    def post_separated_symbol(self, symbol: SeparatedSymbol) -> None:
        symbol.type = ["list", *symbol.symbol.type]

    def post_symbol_sequence(self, symbol: SymbolSequence) -> None:
        symbol.type = [[sym.type for sym in symbol.symbols]]

    def post_group_symbol(self, symbol: GroupSymbol) -> None:
        if symbol.multiple:
            symbol.type = ["list", symbol.symbols.type]
        elif symbol.optional:
            symbol.type = ["Optional", symbol.symbols.type]
        else:
            symbol.type = [*symbol.symbols.type]

    def run(self) -> None:
        walk_front(self.front, self)
