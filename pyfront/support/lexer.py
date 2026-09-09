import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, TypeVar

from pyfront.support.errors import SyntaxError
from pyfront.support.position import Position

logger = logging.getLogger(__name__)


T = TypeVar("T", bound=Enum)
O = TypeVar("O")


@dataclass
class Token[T]:
    type: T
    value: str | None
    position: Position

    def record(self, obj: O) -> O:
        return self.position.record(obj)


class TokenDef[T](Protocol):
    WhitespaceRegexs: dict[str, str]
    LiteralText: dict[T, str]
    TokenRegex: dict[T, str]


class Lexer[T]:
    def __init__(self, tokens: TokenDef[T], source_code: str, eof_token: T):
        self.token_def = tokens
        self.source_code = source_code
        self.position = Position.start_of_file()
        self.current_char = self.source_code[self.position.charno] if self.source_code else None
        self.eof_token = eof_token

    def advance(self, match: str) -> Position:
        """Advance the position and update the current character.

        Args:
            match (str): The matched string to advance past.

        Returns:
            Position: The starting position before advancing.
        """
        old_position = self.position
        self.position = self.position.advance(match)

        if self.position.charno < len(self.source_code):
            self.current_char = self.source_code[self.position.charno]
        elif self.current_char is not None:
            self.current_char = None
        return old_position

    def skip_whitespace(self) -> None:
        """Skip whitespace characters and comments."""
        while self.current_char is not None:
            for regex in self.token_def.WhitespaceRegexs:
                match = re.match(regex, self.source_code[self.position.charno :])
                if match:
                    self.advance(match.group(0))
                    break
            else:
                break  # No whitespace or comment found

    def get_next_token(self) -> Token[T]:
        """Lexical analysis: return the next token from the input."""
        self.skip_whitespace()
        if self.current_char is None:
            return Token(self.eof_token, "", self.position)  # Return EOF token
        best_match = ""
        best_token_type = None
        token_value = None
        for token_type, text in self.token_def.LiteralText.items():
            match = re.match(text, self.source_code[self.position.charno :])
            if match and len(match.group(0)) > len(best_match):
                best_token_type = token_type
                best_match = match.group(0)

        for token_type, regex in self.token_def.TokenRegex.items():
            match = re.match(regex, self.source_code[self.position.charno :])
            if match and len(match.group(0)) > len(best_match):
                best_token_type = token_type
                best_match = match.group(0)
                token_value = best_match
        if best_token_type is not None:
            return Token(best_token_type, token_value, self.advance(best_match))

        raise SyntaxError(self.position, self.current_char)

    def __iter__(self):
        """Make the lexer iterable."""
        return self

    def __next__(self) -> Token[T]:
        """Return the next token or raise StopIteration."""
        return self.get_next_token()
