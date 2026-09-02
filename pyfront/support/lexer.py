import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, TypeVar

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Position:
    charno: int
    line: int
    column: int


class SyntaxError(Exception):
    """Custom exception for syntax errors in the lexer."""

    def __init__(self, character: str, position: Position):
        super().__init__(f"Unexpected character: {character} at {position.line}:{position.column}")
        self.character = character
        self.position = position


T = TypeVar("T", bound=Enum)


@dataclass
class Token[T]:
    type: T
    value: str | None
    position: Position


class TokenDef[T](Protocol):
    WhitespaceRegexs: dict[str, str]
    LiteralText: dict[T, str]
    TokenRegex: dict[T, str]


class Lexer[T]:
    def __init__(self, tokens: TokenDef[T], source_code: str, eof_token: T):
        self.token_def = tokens
        self.source_code = source_code
        self.position = Position(charno=0, line=1, column=1)
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
        num_newlines = match.count("\n")
        new_col = self.position.column if num_newlines == 0 else 1
        new_col += len(match.split("\n")[-1])
        self.position = Position(
            charno=self.position.charno + len(match),
            line=self.position.line + num_newlines,
            column=new_col,
        )

        if self.position.charno < len(self.source_code):
            self.current_char = self.source_code[self.position.charno]
        elif self.current_char != self.eof_token:
            self.current_char = self.eof_token
        else:
            self.current_char = None  # End of input
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

    def get_next_token(self) -> Token[T] | None:
        """Lexical analysis: return the next token from the input."""
        self.skip_whitespace()
        if self.current_char == self.eof_token:
            return Token(self.eof_token, "", self.position)  # Return EOF token
        if self.current_char is None:
            return None  # End of input
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

        raise SyntaxError(self.current_char, self.position)

    def __iter__(self):
        """Make the lexer iterable."""
        return self

    def __next__(self) -> Token[T]:
        """Return the next token or raise StopIteration."""
        token = self.get_next_token()
        if token is None:
            raise StopIteration
        return token
