from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .lexer import Lexer, Token


class Terminals(Enum):
    pass


class NonTerminals(Enum):
    pass


@dataclass
class Label:
    label: str
    value: object

    def unwrap(self) -> tuple[str, object]:
        return self.label, self.value

    @property
    def name(self) -> str:
        return f"{self.label}:{self.value.name}"


class LlSyntaxError(Exception):
    """Custom exception for syntax errors in the LL parser."""

    def __init__(self, token: Token[Terminals], message: str):
        super().__init__(f"{token.position.line}:{token.position.column}: {message}")


class UnexpectedEOF(Exception):
    """Custom exception for unexpected end of input in the LL parser."""

    def __init__(self):
        super().__init__("Unexpected end of input")


class Rule(Protocol):
    terms: list[NonTerminals]

    def build(self, **kwargs: object) -> object:
        raise NotImplementedError


class Grammar(Protocol):
    rules: list[Rule]
    parse_table: dict[str, dict[str, int]]
    start: NonTerminals


class Reduce:
    def __init__(self, rule: Rule):
        self.rule = rule
        self.count = len(rule.terms)

    @property
    def name(self) -> str:
        return self.rule.__class__.__name__

    def build(self, values: list[tuple[str | None, object]]) -> object:
        kwargs = {label: value for label, value in values if label is not None}
        return self.rule.build(**kwargs)


class LlParser:
    def __init__(self, grammar: Grammar):
        self.grammar = grammar

    def parse(self, tokens: Lexer[Terminals]) -> object:
        stack: list[Reduce | Label | Terminals | NonTerminals] = [
            tokens.eof_token,
            self.grammar.start,
        ]

        values: list[tuple[str | None, object]] = []
        tokens = iter(tokens)
        current_token = next(tokens, None)
        while stack:
            print(
                f"Values: {values}\nCurrent Token: {current_token.type if current_token else None} Stack: {[item.name for item in reversed(stack)]}\n"
            )
            top = stack.pop()
            if isinstance(top, Label):
                label, top = top.unwrap()
            else:
                label = None
            if isinstance(top, Reduce):
                # All children parsed; their values are the last `count` on the value stack
                children = values[len(values) - top.count :]
                del values[len(values) - top.count :]
                values.append((label, top.build(children)))
            elif isinstance(top, Terminals):
                if current_token.type == top:
                    values.append((label, current_token.value))
                    current_token = next(tokens, None)

                else:
                    raise LlSyntaxError(
                        current_token, f"Unexpected {current_token.type}, expected: {top}"
                    )
            elif isinstance(top, NonTerminals):
                if current_token is None:
                    raise UnexpectedEOF()

                if current_token.type in self.grammar.parse_table[top]:
                    next_rule = self.grammar.rules[
                        self.grammar.parse_table[top][current_token.type]
                    ]
                    stack.append(Label(label, Reduce(next_rule)))
                    for term in reversed(next_rule.terms):
                        stack.append(term)
                else:
                    raise LlSyntaxError(current_token, f"Unexpected {current_token.type}")

        return values[0][1] if values else None
