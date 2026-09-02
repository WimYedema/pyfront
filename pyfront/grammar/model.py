from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Self


class TermValueType(Enum):
    NONE = auto()
    DIRECT = auto()
    TUPLE = auto()
    LIST = auto()
    DICT = auto()


class Parameter:
    def __init__(
        self,
        value: str | None,
        type_: TermValueType = TermValueType.DIRECT,
        name: str | None = None,
    ):
        self.name = name
        self.value = value
        self.type_ = type_

    @classmethod
    def list(cls, value: str) -> Self:
        return cls(value, TermValueType.LIST)

    @classmethod
    def dict(cls, value: str) -> Self:
        return cls(value, TermValueType.DICT)

    def __str__(self) -> str:
        field_str = f"{self.name}=" if self.name is not None else ""
        type_map = {
            TermValueType.NONE: "NONE:",
            TermValueType.DIRECT: field_str,
            TermValueType.TUPLE: "tuple:",
            TermValueType.LIST: "*",
            TermValueType.DICT: "**",
        }
        return f"{type_map[self.type_]}{self.value}"


class RuleValue:
    def __init__(self, constructor: str | None, fields: list[Parameter]):
        if constructor is None and len(fields) > 1:
            raise ValueError("If constructor is None, there must be at most one field")
        self.constructor = constructor
        self.fields = fields

    def arguments(self) -> list[str]:
        return [field.value for field in self.fields if field.value is not None]

    @classmethod
    def forward(cls, value: str) -> RuleValue:
        return RuleValue(None, [Parameter(value)])

    @classmethod
    def none(cls) -> RuleValue:
        return RuleValue(None, [])

    def is_none(self) -> bool:
        return self.constructor is None and len(self.fields) == 0

    def __str__(self) -> str:
        fields_str = ", ".join(str(field) for field in self.fields)
        if self.constructor is None:
            return fields_str
        return f"{self.constructor}({fields_str})"


class Term:
    label: str | None = None
    value_type: TermValueType = TermValueType.DIRECT

    def set_label(self, label: str) -> Self:
        if self.label is not None:
            raise ValueError("Label already set")
        self.label = label
        return self

    def set_value_type(self, value_type: TermValueType) -> Self:
        self.value_type = value_type
        return self

    def make_param(self, name: str | None = None, value: str | None = None) -> Parameter:
        return Parameter(name or self.label, self.value_type, name=value or self.label)


class TerminalTerm(Term):
    def __init__(self, name: str, value: str, prio: int = 0):
        self.name = name
        self.value = value
        self.prio = prio

    def __str__(self):
        if self.label:
            return f"{self.label}:{self.name}({self.value})"
        return f'"{self.value}"'


class NonTerminalTerm(Term):
    def __init__(self, nt: NonTerminal):
        self.nt = nt

    @property
    def name(self) -> str:
        return self.nt.name

    def __str__(self):
        if self.label:
            return f"{self.label}:{self.name}"
        return self.name


class NonTerminal:
    def __init__(self, name: str):
        self.name = name
        self.rules: list[Rule] = []

    def __str__(self):
        result = f"{self.name}:\n"
        for rule in self.rules:
            result += f"  {str(rule)}\n"
        return result

    def add_rule(self, terms: list[Term], value: RuleValue, produce_count: int = 1) -> Rule:
        rule = Rule(self, terms, value)
        rule.produce_count = produce_count
        self.rules.append(rule)
        return rule

    def remove_rule(self, rule: Rule) -> None:
        self.rules.remove(rule)
        rule.nt = None

    def term(self) -> NonTerminalTerm:
        return NonTerminalTerm(self)


class Rule:
    def __init__(self, nt: NonTerminal, terms: list[Term], value: RuleValue):
        self.nt = nt
        self.terms = terms
        self.value = value
        self.produce_count = 1

    @property
    def name(self) -> str:
        index = self.nt.rules.index(self)
        return f"{self.nt.name}.{index}"

    @property
    def arguments(self) -> list[str]:
        return self.value.arguments()

    def __str__(self):
        return f"{self.nt.name}({', '.join(self.arguments)}):{self.produce_count} ::= {' '.join(str(term) for term in self.terms)}\t{{ {str(self.value)} }}"


@dataclass
class Grammar:
    start: NonTerminal | None = None
    _nt_map: dict[str, NonTerminal] = field(default_factory=dict)
    terminals: set[TerminalTerm] = field(default_factory=set)

    def __str__(self) -> str:
        result = ""
        for nt in self.non_terminals:
            result += f"{str(nt)}\n"
        return result

    @property
    def rules(self) -> Iterable[Rule]:
        for nt in self.non_terminals:
            yield from nt.rules

    @property
    def non_terminals(self) -> Iterable[NonTerminal]:
        current = dict(self._nt_map)
        visited = set()
        while current:
            yield from current.values()
            visited.update(current.keys())
            current = {k: v for k, v in self._nt_map.items() if k not in visited}

    def add_nt(self, prefix: str) -> NonTerminal:
        """Generate a new non-terminal name based on the given prefix."""
        index = len(self._nt_map)
        name = f"{prefix}_{index}"
        nt = NonTerminal(name)
        self._nt_map[name] = nt
        return nt

    def get_nt(self, name: str) -> NonTerminal:
        """Get an existing non-terminal by name, or create a new one if it doesn't exist."""
        if name not in self._nt_map:
            self._nt_map[name] = NonTerminal(name)
        return self._nt_map[name]

    def remove_nt(self, name: str) -> None:
        """Remove a non-terminal from the grammar."""
        if name in self._nt_map:
            del self._nt_map[name]

    def ref_term(self, name: str) -> TerminalTerm | NonTerminalTerm:
        """Get a reference to an existing terminal or non-terminal by name."""
        for term in self.terminals:
            if term.name == name:
                return term
        return self.ref_nt(name)

    def ref_nt(self, name: str) -> NonTerminalTerm:
        """Get a reference to an existing non-terminal by name, or create a new one if it doesn't exist."""
        return self.get_nt(name).term()

    def add_rule(self, name: str, terms: list[Term], value: RuleValue) -> Rule:
        return self.get_nt(name).add_rule(terms, value)

    def copy_rules(self, *rules: Rule) -> None:
        for rule in rules:
            self.add_rule(rule.nt.name, rule.terms, rule.value)

    def add_terminal(self, name: str, value: str, prio: int = 0) -> TerminalTerm:
        type_ = TermValueType.DIRECT if prio == 2 else TermValueType.NONE
        term = TerminalTerm(name, value, prio).set_value_type(type_)
        if name not in {t.name for t in self.terminals}:
            self.terminals.add(term)
        return term

    def with_left_factoring(self) -> Self:
        from .left_factoring import LeftFactoring

        return LeftFactoring(self).compute()
