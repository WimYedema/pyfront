import unittest
from enum import Enum, auto

from pyfront.support.lexer import Lexer, SyntaxError, Token


class TokenType(Enum):
    STRING = auto()
    IDENT = auto()
    INT = auto()
    FLOAT = auto()
    _EOF = auto()


class Tokenizer:
    LiteralText = {}
    TokenRegex = {
        TokenType.STRING: r'\"[^"]*\"',
        TokenType.IDENT: r"[a-zA-Z_][a-zA-Z0-9_]*",
        TokenType.INT: r"\d+",
        TokenType.FLOAT: r"\d+\.\d+",
    }
    WhitespaceRegexs = {
        r"\s+",  # whitespace
        r"//.*",  # single-line comment"
        r"/\*[\s\S]*?\*/",  # multi-line comment"
    }


class LexerTests(unittest.TestCase):
    def _collect_tokens(self, source_code: str) -> list[Token]:
        tokenizer = Tokenizer()
        lexer = Lexer(tokens=tokenizer, source_code=source_code, eof_token=TokenType._EOF)
        tokens: list[Token] = []

        while True:
            token = lexer.get_next_token()
            if token.type == TokenType._EOF:
                return tokens
            tokens.append(token)

    def test_empty_input_returns_no_tokens(self) -> None:
        self.assertEqual([], self._collect_tokens(""))

    def test_float_is_tokenized_before_int(self) -> None:
        tokens = self._collect_tokens("12.34 56")

        self.assertEqual([TokenType.FLOAT, TokenType.INT], [token.type for token in tokens])
        self.assertEqual(["12.34", "56"], [token.value for token in tokens])

    def test_token_positions_track_whitespace_and_newlines(self) -> None:
        tokens = self._collect_tokens("a\n  b")

        self.assertEqual(TokenType.IDENT, tokens[0].type)
        self.assertEqual((1, 1), (tokens[0].position.line, tokens[0].position.column))
        self.assertEqual(TokenType.IDENT, tokens[1].type)
        self.assertEqual((2, 3), (tokens[1].position.line, tokens[1].position.column))

    def test_comments_are_skipped(self) -> None:
        source_code = "a // comment\n /* block */ b"
        tokens = self._collect_tokens(source_code)

        self.assertEqual([TokenType.IDENT, TokenType.IDENT], [token.type for token in tokens])
        self.assertEqual(["a", "b"], [token.value for token in tokens])

    def test_keyword_prefix_identifiers_are_not_split(self) -> None:
        tokens = self._collect_tokens("ROOTX SCANY")

        self.assertEqual([TokenType.IDENT, TokenType.IDENT], [token.type for token in tokens])
        self.assertEqual(["ROOTX", "SCANY"], [token.value for token in tokens])

    def test_multiline_comment_with_newline_updates_following_position(self) -> None:
        tokens = self._collect_tokens("a/*one\n two*/b")

        self.assertEqual([TokenType.IDENT, TokenType.IDENT], [token.type for token in tokens])
        self.assertEqual(["a", "b"], [token.value for token in tokens])
        self.assertEqual((1, 1), (tokens[0].position.line, tokens[0].position.column))
        self.assertEqual((2, 7), (tokens[1].position.line, tokens[1].position.column))

    def test_unexpected_character_raises_syntax_error_with_position(self) -> None:
        lexer = Lexer(tokens=Tokenizer(), source_code="@", eof_token=TokenType._EOF)

        with self.assertRaises(SyntaxError) as context:
            lexer.get_next_token()

        error = context.exception
        self.assertEqual("@", error.character)
        self.assertEqual((1, 1), (error.position.line, error.position.column))


if __name__ == "__main__":
    unittest.main()
