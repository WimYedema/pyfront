from collections.abc import Iterable
from contextlib import AbstractContextManager, contextmanager
from enum import Enum
from typing import TypeVar

from .lexer import Lexer, Token

T = TypeVar("T", bound=Enum)


class Parser[T]:
    def __init__(self, lexer: Lexer[T]):
        self.lexer = lexer
        self.last_token: Token[T] | None = None
        self.next_token: Token[T] | None = self.lexer.get_next_token()
        self.terminators: list[set[T]] = [set()]

    def advance(self) -> None:
        """Advance to the next token."""
        self.last_token = self.next_token
        self.next_token = self.lexer.get_next_token()
        # print(f"Accepted token: {self.last_token}, next token: {self.next_token}")

    def match(self, token_type: T) -> bool:
        """Check if the next token matches the given type."""
        result = self.next_token is not None and self.next_token.type == token_type
        if result:
            self.advance()  # Move to the next token after checking
        return result

    def expect(self, token_type: T) -> str | None:
        """Expect the next token to match the given type, raise an error if not."""
        if not self.match(token_type):
            raise SyntaxError(f"Expected token type {token_type}, got {self.next_token}")
        return self.last_token.value

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
            yield

    def repeat(self, *until: T, separator: T | None = None) -> Iterable[None]:
        with self.terminator(*until):
            yield from self.multiple(separator)
