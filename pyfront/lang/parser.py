from collections.abc import Iterable
from contextlib import AbstractContextManager, contextmanager
from enum import Enum
from typing import TypeVar

from pyfront.support.lexer import Lexer, Token

T = TypeVar("T", bound=Enum)


class Parser[T]:
    def __init__(self, lexer: Lexer[T]):
        self.lexer = lexer
        self._tokens = []
        self._cursor = 0
        self.terminators: list[set[T]] = [set()]

    @property
    def next_token(self) -> Token[T] | None:
        while self._cursor >= len(self._tokens):
            token = self.lexer.get_next_token()
            self._tokens.append(token)
        return self._tokens[self._cursor]

    @property
    def last_token(self) -> Token[T] | None:
        return self._tokens[self._cursor - 1] if self._cursor > 0 else None

    def peek_token(self, ahead: int = 1) -> Token[T] | None:
        while self._cursor + ahead >= len(self._tokens):
            token = self.lexer.get_next_token()
            self._tokens.append(token)
        return self._tokens[self._cursor + ahead]

    def advance(self, amount: int = 1) -> None:
        """Advance to the next token."""
        self._cursor += amount

    def match(self, *token_type: T) -> tuple[str] | str | None:
        """Check if the next token matches the given type."""
        result = []
        for i, tt in enumerate(token_type):
            token = self.peek_token(i)
            if token is None or token.type != tt:
                return None
            result.append(token.value)
        self.advance(i + 1)  # Move to the next token after checking
        if len(result) == 1:
            return result[0]
        return tuple(result)

    def expect(self, *token_type: T) -> tuple[str, ...] | str | None:
        """Expect the next token to match the given type, raise an error if not."""
        result = self.match(*token_type)
        if result is None:
            raise SyntaxError(f"Expected token type {token_type}, got {self.next_token}")
        return result

    def push_terminator(self, *tokens: T) -> None:
        """Push a terminator token onto the stack."""
        self.terminators.append(set(tokens))

    def pop_terminator(self, *tokens: T) -> T | None:
        """Pop a terminator token from the stack."""
        if not self.terminators or not set(tokens).issubset(set(self.terminators[-1])):
            raise SyntaxError(f"Unexpected terminator: {tokens}")
        self.terminators.pop()
        return self.next_token.type if self.next_token else None

    @contextmanager
    def terminator(self, *tokens: T) -> AbstractContextManager[None]:
        """Context manager for handling terminators."""
        self.push_terminator(*tokens)
        try:
            yield
        finally:
            self.pop_terminator(*tokens)
            self.advance()  # Move past the terminator token

    def multiple(self, separator: T | None = None) -> Iterable[None]:
        first = True
        while self.next_token is not None and self.next_token.type not in self.terminators[-1]:
            if not first and separator is not None:
                if not self.match(separator):
                    break
            first = False
            if separator is None:
                yield
            else:
                new_terminators = [separator, *self.terminators[-1]]
                self.push_terminator(*new_terminators)
                yield
                self.pop_terminator(*new_terminators)

    def repeat(self, *until: T, separator: T | None = None) -> Iterable[None]:
        with self.terminator(*until):
            yield from self.multiple(separator)
