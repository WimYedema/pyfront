from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Self

import pyfront.grammar.model as gm
import pyfront.types.model as types


class StackValue:
    def __init__(
        self,
        name: str,
        type: types.Type,
    ):
        self.name = name
        self.type = type

    def __str__(self) -> str:
        return f"{self.name}: {self.type.name}"


class RuleValue:
    stack: list[StackValue]

    def __init__(self, stack: list[StackValue]):
        self.stack = stack

    def arguments(self) -> list[str]:
        return [field.name for field in self.stack]

    def is_no_value(self) -> bool:
        return False

    def __str__(self) -> str:
        return ", ".join(str(field) for field in self.stack)


class NoValue(RuleValue):
    def __init__(self):
        super().__init__([])

    def is_no_value(self) -> bool:
        return True


class ExprValue(RuleValue):
    expression: gm.Expression

    def __init__(self, expression: gm.Expression):
        self.expression = expression
        super().__init__([])

    def __str__(self) -> str:
        return str(self.expression)


class ConstructValue(RuleValue):
    construct_type: types.Type

    def __init__(self, construct_type: types.Type, stack: list[StackValue]):
        self.construct_type = construct_type
        super().__init__(stack)

    def __str__(self) -> str:
        return super().__str__() + f" --> {self.construct_type.name}"


class Term:
    label: str | None = None
    type: types.Type | None

    def set_label(self, label: str) -> Self:
        if self.label is not None:
            raise ValueError("Label already set")
        self.label = label
        return self

    def make_param(self, name: str) -> StackValue:
        return StackValue(name, self.type)


class TerminalTerm(Term):
    def __init__(self, name: str, value: str, prio: int = 0, type: types.Type | None = None):
        self.name = name
        self.value = value
        self.prio = prio
        self.type = type or types.none_type

    def __str__(self):
        if self.label:
            return f"{self.label}:{self.name}({self.value})"
        return f'"{self.value}"'

    def copy(self) -> TerminalTerm:
        return TerminalTerm(self.name, self.value, self.prio, self.type)


class NonTerminalTerm(Term):
    def __init__(self, nt: NonTerminal):
        self.nt = nt

    @property
    def type(self) -> types.Type | None:
        return self.nt.type

    @property
    def name(self) -> str:
        return self.nt.name

    def __str__(self):
        if self.label:
            return f"{self.label}:{self.name}"
        return self.name


class NonTerminal:
    name: str
    rules: list[Rule]
    type: types.Type | None = None

    def __init__(self, name: str, type: types.Type | None = None):
        self.name = name
        self.rules: list[Rule] = []
        self.type = type

    def __str__(self):
        result = f"{self.name}({self.type}):\n"
        for rule in self.rules:
            result += f"  {str(rule)}\n"
        return result

    def add_rule(self, terms: list[Term], value: RuleValue) -> Rule:
        rule = Rule(self, terms, value)
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

    @property
    def name(self) -> str:
        index = self.nt.rules.index(self)
        return f"{self.nt.name}.{index}"

    @property
    def arguments(self) -> list[str]:
        return self.value.arguments()

    def __str__(self):
        return f"{self.nt.name} ::= {' '.join(str(term) for term in self.terms)}\t{{ {str(self.value)} }}"


@dataclass
class Grammar:
    predefined_terminals = {
        "String": TerminalTerm("String", r"""r'\"[^"]*\"'""", type=types.string_type, prio=2),
        "Ident": TerminalTerm(
            "Ident", r'''r"[a-zA-Z_][a-zA-Z0-9_]*"''', type=types.string_type, prio=2
        ),
        "Int": TerminalTerm("Int", r'''r"\d+"''', type=types.int_type, prio=2),
        "Float": TerminalTerm("Float", r'''r"\d+\.\d+"''', type=types.float_type, prio=2),
    }

    start: NonTerminal | None = None
    _nt_map: dict[str, NonTerminal] = field(default_factory=dict)
    terminals: set[TerminalTerm] = field(default_factory=set)

    def __post_init__(self):
        for term in self.predefined_terminals.values():
            self.terminals.add(term)

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

    def add_nt(
        self, name: str | None = None, type: types.Type | None = None, *, prefix: str | None = None
    ) -> NonTerminal:
        """Generate a new non-terminal name based on the given prefix."""
        index = len(self._nt_map)
        if name is None:
            name = f"{prefix}_{index}"
        elif prefix is not None:
            raise ValueError("Cannot specify both name and prefix")
        if name in self._nt_map:
            nt = self._nt_map[name]
            if type is not None:
                if nt.type is not None and nt.type != type:
                    raise ValueError(f"Non-terminal {name} already exists with a different type")
                else:
                    nt.type = type
        else:
            nt = NonTerminal(name, type=type)
            self._nt_map[name] = nt
        return nt

    def find_nt(self, name: str) -> NonTerminal:
        """Find an existing non-terminal by name."""
        return self._nt_map[name]

    def remove_nt(self, name: str) -> None:
        """Remove a non-terminal from the grammar."""
        if name in self._nt_map:
            del self._nt_map[name]

    def find_term(self, name: str) -> TerminalTerm | NonTerminalTerm:
        """Get a reference to an existing terminal or non-terminal by name."""
        for term in self.terminals:
            if term.name == name:
                return term.copy()  # don't copy label
        return self.find_nt(name).term()

    def add_terminal(
        self, name: str, value: str, prio: int = 0, type: types.Type | None = None
    ) -> TerminalTerm:
        term = TerminalTerm(name, value, prio, type=type or types.none_type)
        if name not in {t.name for t in self.terminals}:
            self.terminals.add(term)
        return term

    def with_left_factoring(self) -> Self:
        from .left_factoring import LeftFactoring

        return LeftFactoring(self).compute()
