import logging
from enum import Enum
from typing import Protocol

from .lexer import Lexer, Token

logger = logging.getLogger(__name__)

undefined = object()


class Terminals(Enum):
    pass


class NonTerminals(Enum):
    pass


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
    argument_names: list[str]

    def build(self, **kwargs: object) -> object:
        raise NotImplementedError


class Grammar(Protocol):
    rules: list[Rule]
    parse_table: dict[str, dict[str, int]]
    start: NonTerminals


class Reduce:
    def __init__(self, rule: Rule):
        self.rule = rule
        self.argument_names = rule.argument_names

    @property
    def name(self) -> str:
        return self.rule.__class__.__name__

    def reduce(self, values: list[object]) -> object:
        assert len(values) == len(self.argument_names), (
            f"Expected {len(self.argument_names)} values, got {len(values)}"
        )

        kwargs = {label: value for label, value in zip(self.argument_names, values, strict=True)}
        return self.rule.build(**kwargs)

    def __str__(self) -> str:
        return f"Reduce({self.name})"


class LlParser:
    def __init__(self, grammar: Grammar):
        self.grammar = grammar

    def parse(self, tokens: Lexer[Terminals]) -> object:
        stack: list[Reduce | Terminals | NonTerminals] = [
            tokens.eof_token,
            self.grammar.start,
        ]

        values: list[object] = []
        tokens = iter(tokens)
        current_token = next(tokens, None)
        while stack:
            logger.debug(
                "Values: %s",
                values,
            )
            logger.debug(
                "current token: %s(%s)",
                current_token.type if current_token else None,
                current_token.value if current_token else None,
            )
            logger.debug(
                "stack: %s",
                " ".join(item.name for item in reversed(stack)),
            )
            top = stack.pop()
            if isinstance(top, Reduce):
                count = len(top.argument_names)
                children = values[len(values) - count :]
                logger.debug(
                    "reducing %s with children: %s",
                    top.name,
                    children,
                )
                del values[len(values) - count :]
                rv = top.reduce(children)
                if rv is not undefined:
                    values.append(rv)
            elif isinstance(top, Terminals):
                if current_token.type == top:
                    values.append(current_token.value)
                    current_token = next(tokens, None)

                else:
                    raise LlSyntaxError(
                        current_token,
                        f"Unexpected {current_token.type}:{current_token.value}, expected: {top}",
                    )
            elif isinstance(top, NonTerminals):
                if current_token is None:
                    raise UnexpectedEOF()

                if current_token.type in self.grammar.parse_table[top]:
                    next_rule = self.grammar.rules[
                        self.grammar.parse_table[top][current_token.type]
                    ]
                    stack.append(Reduce(next_rule))
                    for term in reversed(next_rule.terms):
                        stack.append(term)
                else:
                    raise LlSyntaxError(current_token, f"Unexpected {current_token.type}")

        return values[0] if values else None
