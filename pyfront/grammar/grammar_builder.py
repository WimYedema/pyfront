import re
from collections.abc import Iterable

import pyfront.grammar.model as gm
import pyfront.types.model as types
from pyfront.generate.report import report
from pyfront.lang.model import (
    Choice,
    FalseExpr,
    Front,
    GroupSymbol,
    LabeledSymbol,
    MoreSymbol,
    NoneExpr,
    OptionalSymbol,
    ReferenceSymbol,
    Rule,
    RuleChoice,
    SeparatedSymbol,
    StringSymbol,
    Symbol,
    SymbolsChoice,
    SymbolSequence,
    TrueExpr,
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


class GrammarBuilder(gm.Grammar):
    grammar: gm.Grammar

    def _encode_symbol(self, symbol: Symbol) -> gm.Term:
        match symbol:
            case StringSymbol(value):
                return self._new_terminal(value[1:-1])  # return value
            case LabeledSymbol(label, inner_symbol):
                return self._encode_symbol(inner_symbol).set_label(label)
            case ReferenceSymbol(name, _):
                if name in self.grammar.predefined_terminals:
                    return self.grammar.find_term(name)
                return self.grammar.add_nt(name=name, type=symbol.type).term()
            case SeparatedSymbol(inner_symbol, separator):
                sep = self.grammar.add_nt(type=symbol.type, prefix="separated").term()
                head = self._encode_symbol(inner_symbol)
                tail = sep
                self._add_rule(
                    sep.nt,
                    [head, self._new_terminal(separator[1:-1]), tail],
                    gm.ConstructValue(sep.type, [head.make_param("head"), tail.make_param("tail")]),
                )
                self._add_rule(
                    sep.nt, [head], gm.ConstructValue(sep.type, [head.make_param("head")])
                )
                return sep
            case GroupSymbol(symbols):
                return self._encode_symbol_sequence(symbols)

            case OptionalSymbol(symbols=symbols):
                head = self._encode_symbol_sequence(symbols)
                group = self.grammar.add_nt(type=symbol.type, prefix="optional").term()
                self._add_rule(
                    group.nt,
                    [head],
                    gm.NoValue() if head.type != types.none_type else gm.ExprValue(TrueExpr()),
                )
                self._add_rule(
                    group.nt,
                    [],
                    gm.ExprValue(NoneExpr())
                    if head.type != types.none_type
                    else gm.ExprValue(FalseExpr()),
                )
                return group
            case MoreSymbol(symbols=symbols, optional=optional):
                head = self._encode_symbol_sequence(symbols)
                group = self.grammar.add_nt(type=symbol.type, prefix="list").term()
                tail = group.nt.term()
                self._add_rule(
                    group.nt,
                    [head, tail],
                    gm.ConstructValue(
                        group.type, [head.make_param("head"), tail.make_param("tail")]
                    ),
                )
                if optional:
                    self._add_rule(group.nt, [], gm.ConstructValue(group.type, []))
                return group

    def _encode_symbol_sequence(self, symbol_sequence: SymbolSequence) -> gm.Term:
        syms = [self._encode_symbol(symbol) for symbol in symbol_sequence.symbols]
        if len(syms) == 1:
            return syms[0]

        seq = self.grammar.add_nt(prefix="sequence", type=symbol_sequence.type).term()
        match seq.type:
            case types.TupleType():
                tuple_value = gm.ConstructValue(
                    seq.type,
                    [gm.StackValue(f.name, f.type) for f in seq.type.fields],
                )
            case _:
                tuple_value = gm.ConstructValue(seq.type, [gm.StackValue("keep", seq.type)])
        self._add_rule(seq.nt, syms, tuple_value)
        return seq

    def iter_fields(self, *args: types.Type) -> Iterable[types.Field]:
        """Iterate over fields of the given types."""
        for index, t in enumerate(args):
            if isinstance(t, types.CompoundType):
                yield from t.iter_fields()
            else:
                yield types.Field(f"fld{index}", t)

    def _encode_choice(
        self, choice: Choice, nt: gm.NonTerminal, before: list[gm.Term] | None = None
    ) -> None:
        before = before or []
        before_types = [t.type for t in before]
        match choice:
            case SymbolsChoice(symbols=symbols):
                # TODO: Duplicated below
                terms = self._encode_symbol_sequence(symbols)
                if not isinstance(terms.type, types.TupleType) and not before:
                    rv = gm.NoValue()
                else:
                    rv = gm.ConstructValue(
                        nt.type,
                        [
                            gm.StackValue(t.name, t.type)
                            for t in self.iter_fields(*before_types, terms.type)
                        ],
                    )
                self._add_rule(nt, [*before, terms], rv)
            case RuleChoice(rule=rule):
                self._encode_rule(rule, before)
                self._add_rule(nt, [self.grammar.find_nt(rule.name).term()], gm.NoValue())

    def _encode_rule(self, rule: Rule, before: list[gm.Term] | None = None) -> None:
        before = before or []
        before_types = [t.type for t in before]
        nt = self.grammar.add_nt(name=rule.name, type=rule.type)
        report.emit(f"\n## From `{rule}`")
        if rule.choices is not None:
            if rule.terms.symbols:
                shared_terms = [self._encode_symbol_sequence(rule.terms)]
            else:
                shared_terms = []
            for choice in rule.choices:
                self._encode_choice(choice, nt, [*before, *shared_terms])

        elif rule.choices is None:
            terms = self._encode_symbol_sequence(rule.terms)

            if not isinstance(terms.type, types.TupleType):
                rv = gm.NoValue()
            else:
                rv = gm.ConstructValue(
                    nt.type,
                    [
                        gm.StackValue(t.name, t.type)
                        for t in self.iter_fields(*before_types, terms.type)
                    ],
                )
            self._add_rule(nt, [*before, terms], rv)

        report.emit("")

    def _new_terminal(
        self,
        name: str,
    ) -> gm.TerminalTerm:
        """Generate a new terminal based on the given value."""
        value = f'r"{re.escape(name)}"'
        prio = 0 if name.isalnum() else 1

        return self.grammar.add_terminal(_make_token_name(name), value, prio)

    def _add_rule(
        self,
        nt: gm.NonTerminal,
        terms: list[gm.Term],
        code: gm.RuleValue,
    ) -> gm.Rule:
        rule = nt.add_rule(terms, code)
        report.emit(f"* {str(rule)}\n    {{ return {code} }}")
        report.nt_info(rule.nt.name, f"rule {rule.name}", str(rule))
        return rule

    def build(self, front: Front) -> gm.Grammar:
        self.grammar = gm.Grammar()
        report.emit("# Grammar construction\n")
        for rule in front.rules:
            self._encode_rule(rule)
            if rule.is_root:
                self.grammar.start = self.grammar.find_nt(rule.name)

        if self.grammar.start is None:
            self.grammar.start = self.grammar.find_nt(front.rules[0].name)

        report.emit("\n# Initial Grammar\n")
        report.emit(f"{self.grammar}")

        return self.grammar
