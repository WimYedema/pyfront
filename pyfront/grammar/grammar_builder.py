import re

import pyfront.grammar.model as gm
from inflection import camelize
from pyfront.generate.report import report
from pyfront.lang.model import (
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
from pyfront.lang.walk import walk_symbol_sequence


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


class CollectLabels:
    def __init__(self):
        self.labels = list()

    def pre_labeled_symbol(self, labeled_symbol: LabeledSymbol) -> None:
        """Collect labels from LabeledSymbol instances."""
        self.labels.append(labeled_symbol.label)


class GrammarBuilder(gm.Grammar):
    grammar: gm.Grammar

    def _encode_symbol(self, symbol: Symbol) -> gm.Term:
        match symbol:
            case StringSymbol(value):
                return self._new_terminal(value[1:-1])  # return value
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
                    return self._new_terminal(keyword, predef[keyword])
                return self.grammar.ref_nt(keyword)
            case SeparatedSymbol(symbol, separator):
                sep = self.grammar.add_nt("separated").term()
                head = self._encode_symbol(symbol).set_label("head")
                tail = (
                    self.grammar.ref_nt(sep.name)
                    .set_label("tail")
                    .set_value_type(gm.TermValueType.LIST)
                )
                self._add_rule(
                    sep,
                    [head, self._new_terminal(separator[1:-1]), tail],
                    gm.RuleValue("list", [head.make_param(), tail.make_param()]),
                )
                self._add_rule(sep, [head], gm.RuleValue("list", [head.make_param()]))
                return sep
            case GroupSymbol(symbols, optional, multiple):
                head, last_rule = self._encode_symbol_sequence(symbols)
                if not multiple and not optional:
                    return head
                group = self.grammar.add_nt("group").term()
                if multiple:
                    tail = (
                        self.grammar.ref_nt(group.name)
                        .set_label("tail")
                        .set_value_type(gm.TermValueType.LIST)
                    )
                    self._add_rule(
                        group,
                        [head.set_label("head"), tail],
                        gm.RuleValue("list", [head.make_param(), tail.make_param()]),
                    )
                    if optional:
                        self._add_rule(group, [], gm.RuleValue("list", []))
                    group.set_value_type(gm.TermValueType.LIST)
                elif optional:
                    group.set_value_type(gm.TermValueType.DICT)
                    self._add_rule(
                        group,
                        [head],
                        gm.RuleValue.none(),
                    )
                    self._add_rule(
                        group,
                        [],
                        gm.RuleValue(
                            "dict",
                            [
                                gm.Parameter(None, name=value.name)
                                for value in last_rule.value.fields
                                if value.name is not None
                            ],
                        ),
                    )
                else:
                    self._add_rule(group, head, last_rule.value, last_rule.produce_count)
                return group

    def _encode_symbol_sequence(self, symbol_sequence: SymbolSequence) -> tuple[gm.Term, gm.Rule]:
        seq = self.grammar.add_nt("sequence").term()
        syms = [self._encode_symbol(symbol) for symbol in symbol_sequence.symbols]
        tuple_value = gm.RuleValue(
            "dict", [sym.make_param() for sym in syms if sym.label is not None]
        )
        rule = self._add_rule(seq, syms, tuple_value, len(tuple_value.fields))
        return seq.set_value_type(gm.TermValueType.DICT), rule

    def _encode_rule(self, rule: Rule) -> None:
        if rule.is_ref:
            return
        report.emit(f"\n## From `{rule}`")
        if rule.alts is not None and not rule.terms.symbols:
            for alt in rule.alts:
                self._encode_rule(alt)
                term = self.grammar.ref_nt(alt.name)
                self._add_rule(rule.name, [term], gm.RuleValue.none())
        elif rule.alts is None:
            labels = walk_symbol_sequence(rule.terms, CollectLabels()).labels
            terms, _ = self._encode_symbol_sequence(SymbolSequence(symbols=rule.terms.symbols))
            if not terms.label:
                terms.set_label("values")
            self._add_rule(
                rule.name,
                [terms],
                gm.RuleValue(
                    camelize(rule.name), [gm.Parameter(label, name=label) for label in labels]
                ),
            )
        else:
            labels = walk_symbol_sequence(rule.terms, CollectLabels()).labels
            shared_terms, _ = self._encode_symbol_sequence(
                SymbolSequence(symbols=rule.terms.symbols)
            )
            for alt in rule.alts:
                if alt.is_ref:
                    raise ValueError(f"Alternative rule {alt.name} should not be a reference.")
                if alt.alts is not None:
                    raise ValueError(f"Alternative rule {alt.name} should not have alternatives.")
                alt_labels = walk_symbol_sequence(alt.terms, CollectLabels()).labels
                alt_terms, _ = self._encode_symbol_sequence(
                    SymbolSequence(symbols=alt.terms.symbols)
                )
                self._add_rule(
                    rule.name,
                    [shared_terms, alt_terms],
                    gm.RuleValue(
                        camelize(alt.name),
                        [gm.Parameter(label, name=label) for label in labels + alt_labels],
                    ),
                )

        report.emit("")

    def _new_terminal(
        self, name: str, value: str | None = None, prio: int | None = None
    ) -> gm.TerminalTerm:
        """Generate a new terminal based on the given value."""
        if value is None:
            value = f'r"{re.escape(name)}"'
            if prio is None:
                prio = 0 if name.isalnum() else 1
        else:
            prio = 2 if prio is None else prio

        return self.grammar.add_terminal(_make_token_name(name), value, prio)

    def _add_rule(
        self,
        name: str | gm.NonTerminalTerm,
        terms: list[gm.Term],
        code: gm.RuleValue,
        produce_count: int = 1,
    ) -> gm.Rule:
        if not isinstance(name, str):
            name = name.name
        rule = self.grammar.add_rule(name, terms, code)
        rule.produce_count = produce_count
        report.emit(f"* {str(rule)}\n    {{ return {code} }}")
        report.nt_info(rule.nt.name, f"rule {rule.name}", str(rule))
        return rule

    def build(self, front: Front) -> gm.Grammar:
        self.grammar = gm.Grammar()
        self.grammar.start = self.grammar.get_nt(front.rules[0].name)
        report.emit("# Grammar\n")
        for rule in front.rules:
            if rule.is_root:
                self.grammar.start = self.grammar.get_nt(rule.name)
            self._encode_rule(rule)

        report.emit(f"Start: {self.grammar.start.name}")
        if report.is_enabled:
            report.emit("\n## Terminals")
            for t in self.grammar.terminals:
                report.emit(f"* {t.name}: `{t.value}`")

        return self.grammar
