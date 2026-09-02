import re
from collections.abc import Iterable

import pyfront.grammar.model as gm
import pyfront.types.model as types
from pyfront.generate.report import report
from pyfront.lang.model import (
    FalseExpr,
    Front,
    GroupSymbol,
    KeywordSymbol,
    LabeledSymbol,
    NoneExpr,
    Rule,
    SeparatedSymbol,
    StringSymbol,
    Symbol,
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
            case KeywordSymbol(keyword, _):
                if keyword in self.grammar.predefined_terminals:
                    return self.grammar.find_term(keyword)
                return self.grammar.add_nt(name=keyword, type=symbol.type).term()
            case SeparatedSymbol(inner_symbol, separator):
                sep = self.grammar.add_nt(type=symbol.type, prefix="separated").term()
                head = self._encode_symbol(inner_symbol)
                tail = sep
                self._add_rule(
                    sep.nt,
                    [head, self._new_terminal(separator[1:-1]), tail],
                    gm.ConstructValue(
                        sep.nt.type, [head.make_param("head"), tail.make_param("tail")]
                    ),
                )
                self._add_rule(
                    sep.nt, [head], gm.ConstructValue(sep.nt.type, [head.make_param("head")])
                )
                return sep
            case GroupSymbol(symbols, optional, multiple):
                head = self._encode_symbol_sequence(symbols)
                if not multiple and not optional:
                    return head
                if multiple:
                    group = self.grammar.add_nt(type=symbol.type, prefix="list").term()
                    tail = group.nt.term()
                    self._add_rule(
                        group.nt,
                        [head, tail],
                        gm.ConstructValue(
                            group.nt.type, [head.make_param("head"), tail.make_param("tail")]
                        ),
                    )
                    if optional:
                        self._add_rule(group.nt, [], gm.ConstructValue(group.nt.type, []))
                    return group

                elif optional:
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

                else:
                    return head

    def _encode_symbol_sequence(self, symbol_sequence: SymbolSequence) -> gm.Term:
        syms = [self._encode_symbol(symbol) for symbol in symbol_sequence.symbols]
        if len(syms) == 1:
            return syms[0]

        seq = self.grammar.add_nt(prefix="sequence", type=symbol_sequence.type).term()
        match seq.nt.type:
            case types.TupleType():
                tuple_value = gm.ConstructValue(
                    seq.nt.type,
                    [gm.StackValue(f.name, f.type) for f in seq.nt.type.fields],
                )
            case _:
                tuple_value = gm.ConstructValue(seq.nt.type, [gm.StackValue("keep", seq.nt.type)])
        self._add_rule(seq.nt, syms, tuple_value)
        return seq

    def iter_fields(self, *args: types.Type) -> Iterable[types.Field]:
        """Iterate over fields of the given types."""
        for t in args:
            if isinstance(t, types.CompoundType):
                yield from t.iter_fields()

    def _encode_rule(self, rule: Rule) -> None:
        if rule.is_ref:
            return
        nt = self.grammar.add_nt(name=rule.name, type=rule.type)
        report.emit(f"\n## From `{rule}`")
        if rule.alts is not None and not rule.terms.symbols:
            for alt in rule.alts:
                if alt.is_ref:
                    alt_nt = self.grammar.add_nt(name=alt.name)
                else:
                    self._encode_rule(alt)
                    alt_nt = self.grammar.find_nt(alt.name)
                self._add_rule(nt, [alt_nt.term()], gm.NoValue())
        elif rule.alts is None:
            terms = self._encode_symbol_sequence(rule.terms)

            if not isinstance(terms.type, types.TupleType):
                rv = gm.NoValue()
            else:
                rv = gm.ConstructValue(
                    nt.type, [gm.StackValue(t.name, t.type) for t in self.iter_fields(terms.type)]
                )
            self._add_rule(nt, [terms], rv)
        else:
            shared_terms = self._encode_symbol_sequence(rule.terms)
            for alt in rule.alts:
                if alt.is_ref:
                    raise ValueError(f"Alternative rule {alt.name} should not be a reference.")
                if alt.alts is not None:
                    raise ValueError(f"Alternative rule {alt.name} should not have alternatives.")
                alt_terms = self._encode_symbol_sequence(alt.terms)
                self._add_rule(
                    nt,
                    [shared_terms, alt_terms],
                    gm.ConstructValue(
                        alt.type,
                        [gm.StackValue(t.name, t.type) for t in self.iter_fields(alt.type)],
                    ),
                )

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
