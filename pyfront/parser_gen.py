import re
from collections.abc import Iterable
from textwrap import dedent, indent
from typing import Any, TypeVar

from inflection import camelize, underscore

from .ll_grammar import Grammar, NonTerminal, NonTerminalTerm, Term, TerminalTerm
from .ll_grammar import Rule as LlRule
from .model import (
    Front,
    GroupSymbol,
    KeywordSymbol,
    LabeledSymbol,
    Rule,
    SeparatedSymbol,
    StringSymbol,
    Symbol,
    SymbolSequence,
)


def _multi_char_replace_regex(text, replacements):
    pattern = "[" + re.escape("".join(replacements.keys())) + "]"
    return re.sub(pattern, lambda m: replacements[m.group()], text)


def _make_token_name(string: str) -> str:
    """Convert a string into a valid token name."""
    replacements = {
        '"': "DQUOTE",
        "-": "DASH",
        ",": "COMMA",
        ";": "SEMICOLON",
        ":": "COLON",
        "!": "EXCLAMATION",
        ".": "DOT",
        "'": "QUOTE",
        "(": "LPAREN",
        ")": "RPAREN",
        "[": "LBRACKET",
        "]": "RBRACKET",
        "{": "LBRACE",
        "}": "RBRACE",
        "@": "AT",
        "*": "ASTERISK",
        "/": "SLASH",
        "\\": "BSLASH",
        "&": "AMPERSAND",
        "#": "HASH",
        "%": "PERCENT",
        "`": "BACKTICK",
        "^": "CARET",
        "+": "PLUS",
        "<": "LESS_THAN",
        "=": "EQUALS",
        ">": "GREATER_THAN",
        "|": "PIPE",
        "~": "TILDE",
        "$": "DOLLAR",
    }
    return _multi_char_replace_regex(string.upper(), replacements)


class GrammarBuilder:
    def __init__(self):
        self.start: str | None = None
        self.rules = []
        self.rule_code: dict[LlRule, str] = {}
        self.nt_map: dict[str, NonTerminal] = {}
        self.terminals = set()

    def generate_non_terminals(self) -> str:
        code = "class NonTerminals(_NonTerminals):\n"
        for nt in self.nt_map.values():
            code += f"    {underscore(nt.name).upper()} = auto()\n"
        return code + "\n"

    def generate_terminals(self) -> str:
        code = "class Terminals(_Terminals):\n"
        for term in self.terminals:
            code += f"    {term.name} = auto()\n"
        code += "    _EOF = auto()\n"
        return code + "\n"

    def generate_token_map(self) -> str:
        code = "TokenRegex = {\n"
        for term in self.terminals:
            code += f"    Terminals.{term.name}: {term.value},\n"
        code += "}\n"
        return code

    def generate_whitespace_map(self) -> str:
        code = dedent("""\
            WhitespaceRegexs = {
                r"\\s+", # whitespace
                r"//.*",  # single-line comment
            }
            """)
        return code

    def generate_lexer_code(self) -> str:
        code = "class Tokenizer:\n"
        code += indent(self.generate_token_map(), "    ")
        code += indent(self.generate_whitespace_map(), "    ")
        return code + "\n"

    def generate_rule_code(self) -> str:
        code = ""
        for index, rule in enumerate(self.rules):
            args = ["*"]
            args = [f", {term.label}: object" for term in rule.terms if term.label]
            terms = []
            for term in rule.terms:
                if isinstance(term, TerminalTerm):
                    term_text = "Terminals." + term.name
                else:
                    term_text = "NonTerminals." + underscore(term.name).upper()

                if term.label:
                    label = term.label
                    terms.append(f'_Label("{label}", {term_text})')
                else:
                    terms.append(term_text)

            code += dedent(f"""\
                # {str(rule)}
                class Rule{index}{camelize(rule.nt.name)}:
                    terms = [{", ".join(terms)}]

                    def build(self{"".join(args)}) -> object:
                        return {self.rule_code[rule]}

                """)
        return code

    def generate_parse_table(self) -> str:
        code = "parse_table = {\n"
        for nt in self.nt_map.values():
            code += f"    NonTerminals.{underscore(nt.name).upper()}: {{\n"
            for term, rule in self.parse_table[nt].items():
                if isinstance(term, TerminalTerm):
                    code += f"        Terminals.{term.name}: {self.rules.index(rule)},\n"
                elif isinstance(term, NonTerminalTerm):
                    code += f"        NonTerminals.{underscore(term.name).upper()}: {self.rules.index(rule)},\n"
            code += "    },\n"
        code += "}\n"
        return code

    def generate_rules_list(self) -> str:
        code = "rules = [\n"
        for i, rule in enumerate(self.rules):
            code += f"    Rule{i}{camelize(rule.nt.name)}(),\n"
        code += "]\n"
        return code

    def generate_grammar_class(self) -> str:
        code = "class LlGrammar:\n"
        code += f"    start = NonTerminals.{underscore(self.start).upper()}\n"
        code += indent(self.generate_rules_list(), "    ")
        code += indent(self.generate_parse_table(), "    ")
        return code

    def generate_code(self) -> str:
        code = dedent("""\
            from enum import auto

            from pyfront.ll_parser import LlParser as _LlParser
            from pyfront.ll_parser import Terminals as _Terminals
            from pyfront.ll_parser import NonTerminals as _NonTerminals
            from pyfront.ll_parser import Label as _Label
            from pyfront.lexer import Lexer as _Lexer
            """)
        code += self.generate_terminals()
        code += self.generate_lexer_code()
        code += self.generate_non_terminals()
        code += self.generate_rule_code()
        code += self.generate_grammar_class()

        code += dedent("""\
            def parse(text: str) -> object:
                parser = _LlParser(LlGrammar())
                lexer = _Lexer(Tokenizer, text, eof_token=Terminals._EOF)
                return parser.parse(lexer)
            """)
        return code

    def _encode_symbol(self, symbol: Symbol) -> Term:
        match symbol:
            case StringSymbol(value):
                return self.new_terminal(value[1:-1])  # return value
            case LabeledSymbol(label, inner_symbol):
                return self._encode_symbol(inner_symbol).set_label(label)
            case KeywordSymbol(keyword, _):
                predef = {
                    "String": r"""r'\"[^"]*\"'""",
                    "Ident": r'''r"[a-zA-Z_][a-zA-Z0-9_]*"''',
                    "Int": r'''r"\d+"''',
                    "Float": r'''r"\d+\.\d+"''',
                }
                if keyword in predef:
                    return self.new_terminal(keyword, predef[keyword])
                return self.ref_nt(keyword)
            case SeparatedSymbol(symbol, separator):
                sep = self.new_nt("separated")
                inner_term = self._encode_symbol(symbol)
                self.add_rule(
                    sep,
                    [
                        inner_term.set_label("head"),
                        self.new_terminal(separator),
                        self.ref_nt(sep.name).set_label("tail"),
                    ],
                    "[head, *tail]",
                )
                self.add_rule(sep, [inner_term], "[head]")
                return sep
            case GroupSymbol(symbols, optional, multiple):
                inner_term = self._encode_symbol_sequence(symbols)
                if not multiple and not optional:
                    return inner_term
                group = self.new_nt("group")
                if multiple:
                    self.add_rule(
                        group,
                        [inner_term.set_label("head"), self.ref_nt(group.name).set_label("tail")],
                        "[head, *tail]",
                    )
                else:
                    self.add_rule(group, [inner_term.set_label("head")], "[head]")
                if optional:
                    self.add_rule(group, [], "[]")
                return group

    def _encode_symbol_sequence(self, symbol_sequence: SymbolSequence) -> Term:
        if len(symbol_sequence.symbols) == 1:
            return self._encode_symbol(symbol_sequence.symbols[0])
        seq = self.new_nt("sequence")
        syms = [self._encode_symbol(symbol) for symbol in symbol_sequence.symbols]
        self.add_rule(
            seq,
            syms,
            "{" + ", ".join(f'"{sym.label}": {sym.label}' for sym in syms if sym.label) + "}",
        )
        return seq

    def _encode_rule(self, rule: Rule) -> None:
        if rule.alts:
            # Normalization => alt.is_ref for all alts
            return
        else:
            symbols = []
            name = rule.name
            if rule.super_rule:
                name = rule.super_rule.name
                symbols.extend(rule.super_rule.terms.symbols)
            symbols.extend(rule.terms.symbols)
            if rule.super_rule is not None and rule.super_rule.post_terms:
                symbols.extend(rule.super_rule.post_terms.symbols)
            terms = self._encode_symbol_sequence(SymbolSequence(symbols=symbols))
            if not terms.label:
                terms.set_label("values")
            self.add_rule(name, [terms], f"{camelize(rule.name)}(**{terms.label})")

    def new_nt(self, prefix: str) -> NonTerminalTerm:
        """Generate a new non-terminal name based on the given prefix."""
        index = len(self.nt_map)
        name = f"{prefix}_{index}"
        nt = NonTerminal(name)
        self.nt_map[name] = nt
        return NonTerminalTerm(nt.name)

    def ref_nt(self, name: str) -> NonTerminalTerm:
        """Reference an existing non-terminal by name, or create a new one if it doesn't exist."""
        if name not in self.nt_map:
            self.nt_map[name] = NonTerminal(name)
        return NonTerminalTerm(name)

    def new_terminal(self, name: str, value: str | None = None) -> TerminalTerm:
        """Generate a new terminal based on the given value."""
        if value is None:
            value = f'r"{re.escape(name)}"'

        result = TerminalTerm(_make_token_name(name), value)
        if result.name not in {t.name for t in self.terminals}:
            self.terminals.add(result)
        return result

    def add_rule(
        self, name: str | NonTerminalTerm, terms: list[Term], code: str
    ) -> NonTerminalTerm:
        if not isinstance(name, str):
            name = name.name
        if name not in self.nt_map:
            self.nt_map[name] = NonTerminal(name)
        rule = LlRule(self.nt_map[name], terms)
        print(f"added: {str(rule)}")
        self.rules.append(rule)
        self.rule_code[rule] = code
        return NonTerminalTerm(name)

    def build(self, front: Front) -> None:
        self.start = front.rules[0].name
        for rule in front.rules:
            if rule.is_root:
                self.start = rule.name
            self._encode_rule(rule)

        grammar = Grammar(
            rules=self.rules,
            start=self.nt_map[self.start],
        )
        self.parse_table = PopulateParseTable(grammar).compute()


T = TypeVar("T")


def stabilizing_1d[T](check: dict[T, bool]) -> Iterable[dict[T, bool]]:
    """Yield the dict until it stabilizes (no more changes)."""
    old_values = None
    while True:
        new_values = {key for key, value in check.items() if value}
        if new_values != old_values:
            old_values = new_values
            yield check
        else:
            break


def stabilize_2d[T](check: dict[Any, set[T]]) -> Iterable[dict[Any, set[T]]]:
    """Yield the dict until it stabilizes (no more changes)."""
    old_lens = None
    while True:
        new_lens = {key: len(value) for key, value in check.items()}
        if new_lens != old_lens:
            old_lens = new_lens
            yield check
        else:
            break


class PopulateParseTable:
    def __init__(self, grammar: Grammar[LlRule]):
        self.grammar = grammar
        self.nt_map = {rule.nt.name: rule.nt for rule in grammar.rules}
        self.is_nullable = {rule.nt: False for rule in grammar.rules}
        self.first_set = {rule.nt: set() for rule in grammar.rules}
        self.follow_set = {rule.nt: set() for rule in grammar.rules}

    def nt(self, ntt: NonTerminalTerm) -> NonTerminal:
        return self.nt_map[ntt.name]

    def compute_nullable(self) -> None:
        """Compute the nullability of each non-terminal in the grammar."""
        for is_nullable in stabilizing_1d(self.is_nullable):
            for rule in self.grammar.rules:
                if not is_nullable[rule.nt]:
                    if all(
                        isinstance(term, NonTerminalTerm) and is_nullable[self.nt(term)]
                        for term in rule.terms
                    ):
                        is_nullable[rule.nt] = True

    def compute_first_sets(self) -> None:
        for first_set in stabilize_2d(self.first_set):
            for rule in self.grammar.rules:
                for term in rule.terms:
                    if isinstance(term, TerminalTerm):
                        first_set[rule.nt].add(term)
                        break
                    elif isinstance(term, NonTerminalTerm):
                        first_set[rule.nt].update(first_set[self.nt(term)])
                        if not self.is_nullable[self.nt(term)]:
                            break

    def compute_follow_sets(self) -> None:
        self.follow_set[self.grammar.start].add(TerminalTerm("_EOF", ""))

        for follow_set in stabilize_2d(self.follow_set):
            for rule in self.grammar.rules:
                for i, term in enumerate(rule.terms):
                    if isinstance(term, NonTerminalTerm):
                        nt = self.nt(term)
                        for next_term in rule.terms[i + 1 :]:
                            if isinstance(next_term, TerminalTerm):
                                follow_set[nt].add(next_term)
                                break
                            elif isinstance(next_term, NonTerminalTerm):
                                follow_set[nt].update(self.first_set[self.nt(next_term)])
                                if not self.is_nullable[self.nt(next_term)]:
                                    break
                        else:
                            follow_set[nt].update(follow_set[rule.nt])

    def compute_parsing_table(self) -> dict[NonTerminal, dict[Term, Rule]]:
        result: dict[NonTerminal, dict[Term, Rule]] = {rule.nt: {} for rule in self.grammar.rules}
        for rule in self.grammar.rules:
            for term in rule.terms:
                if isinstance(term, TerminalTerm):
                    result[rule.nt][term] = rule
                elif isinstance(term, NonTerminalTerm):
                    for first in self.first_set[self.nt(term)]:
                        result[rule.nt][first] = rule
                    if self.is_nullable[self.nt(term)]:
                        for follow in self.follow_set[rule.nt]:
                            result[rule.nt][follow] = rule
            if self.is_nullable[rule.nt]:
                for follow in self.follow_set[rule.nt]:
                    result[rule.nt][follow] = rule
        return result

    def compute(self) -> dict[NonTerminal, dict[Term, Rule]]:
        self.compute_nullable()
        self.compute_first_sets()
        self.compute_follow_sets()
        return self.compute_parsing_table()
