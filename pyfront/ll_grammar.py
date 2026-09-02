from typing import Self, TypeVar


class Term:
    label: str | None = None

    def set_label(self, label: str) -> Self:
        if self.label is not None:
            raise ValueError("Label already set")
        self.label = label
        return self


class TerminalTerm(Term):
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def __str__(self):
        if self.label:
            return f'{self.label}:"{self.value}"'
        return f'"{self.value}"'


class NonTerminalTerm(Term):
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        if self.label:
            return f"{self.label}:{self.name}"
        return self.name


class NonTerminal:
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name


class Rule:
    def __init__(self, nt: NonTerminal, terms: list[Term]):
        self.nt = nt
        self.terms = terms

    def __str__(self):
        return f"{str(self.nt)} ::= {' '.join(str(term) for term in self.terms)}"


RuleType = TypeVar("RuleType", bound=Rule)


class Grammar[RuleType]:
    rules: list[RuleType]
    parse_table: dict[str, dict[str, int]]

    def __init__(self, start: NonTerminal, rules: list[RuleType]):
        self.start = start
        self.rules = rules
