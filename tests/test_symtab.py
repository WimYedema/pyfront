import unittest

from pyfront.lang.model import Front, KeywordSymbol, Rule, SymbolSequence
from pyfront.symtab import SymbolTable


def rule(name: str, terms: list[KeywordSymbol]) -> Rule:
    return Rule(
        is_root=False,
        name=name,
        super_type=None,
        fields=[],
        terms=SymbolSequence(terms),
        alts=None,
    )


class SymbolTableTests(unittest.TestCase):
    def test_populate_resolves_forward_keyword_references(self) -> None:
        reference = KeywordSymbol("Later")
        earlier = rule("Earlier", [reference])
        later = rule("Later", [])

        symbols = SymbolTable.populate(Front(rules=[earlier, later], scan_rules=[]))

        self.assertIs(later, symbols.symbols["Later"])
        self.assertIs(later, reference.rule)

    def test_populate_rejects_duplicate_rule_names(self) -> None:
        front = Front(rules=[rule("Same", []), rule("Same", [])], scan_rules=[])

        with self.assertRaisesRegex(ValueError, "Duplicate symbol name: Same"):
            SymbolTable.populate(front)


if __name__ == "__main__":
    unittest.main()
