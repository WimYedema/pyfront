import unittest
from enum import auto

from pyfront.support.lexer import Position, Token
from pyfront.support.ll_parser import LlParser, NonTerminals, Terminals, undefined


class Terminal(Terminals):
    VALUE = auto()
    EOF = auto()


class NonTerminal(NonTerminals):
    START = auto()
    ITEM = auto()


class ListLexer:
    def __init__(self, tokens: list[Token[Terminal]]) -> None:
        self.tokens = tokens
        self.eof_token = Terminal.EOF

    def __iter__(self):
        return iter(self.tokens)


class ItemRule:
    terms = [Terminal.VALUE]
    argument_names = ["value"]

    def build(self, **kwargs: object) -> object:
        value = kwargs["value"]
        return (value, str(value).upper())


class StartRule:
    terms = [NonTerminal.ITEM]
    argument_names = ["original", "uppercase"]

    def build(self, **kwargs: object) -> object:
        return kwargs


class UndefinedRule:
    terms = []
    argument_names = []

    def build(self, **kwargs: object) -> object:
        return undefined


class Grammar:
    rules = [StartRule(), ItemRule()]
    parse_table = {
        NonTerminal.START: {Terminal.VALUE: 0},
        NonTerminal.ITEM: {Terminal.VALUE: 1},
    }
    start = NonTerminal.START


class UndefinedGrammar:
    rules = [UndefinedRule()]
    parse_table = {NonTerminal.START: {Terminal.EOF: 0}}
    start = NonTerminal.START


def token(token_type: Terminal, value: str | None) -> Token[Terminal]:
    return Token(token_type, value, Position(charno=0, line=1, column=1))


class LlParserTests(unittest.TestCase):
    def test_parse_reduces_nested_rule_and_flattens_tuple_value(self) -> None:
        tokens = ListLexer([token(Terminal.VALUE, "hello"), token(Terminal.EOF, "")])

        result = LlParser(Grammar()).parse(tokens)

        self.assertEqual({"original": "hello", "uppercase": "HELLO"}, result)

    def test_parse_omits_undefined_reduction_value(self) -> None:
        tokens = ListLexer([token(Terminal.EOF, None)])

        result = LlParser(UndefinedGrammar()).parse(tokens)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
