import unittest

import pyfront.lang.model as lang
import pyfront.types.model as types
from pyfront.types.types_builder import (
    BuildTypes,
    DoubleLabelingError,
    DuplicateLabelError,
    MissingLabelError,
)


def _seq(*symbols: lang.Symbol) -> lang.SymbolSequence:
    return lang.SymbolSequence(list(symbols))


def _rule(name: str, *symbols: lang.Symbol, is_root: bool = False) -> lang.Rule:
    return lang.Rule(
        is_root=is_root,
        name=name,
        super_type=None,
        fields=[],
        terms=_seq(*symbols),
        choices=None,
    )


def _with_super(rule: lang.Rule, super_type: str) -> lang.Rule:
    rule.super_type = super_type
    return rule


def _with_choices(rule: lang.Rule, *choices: lang.Choice) -> lang.Rule:
    rule.choices = list(choices)
    return rule


def _with_fields(rule: lang.Rule, **fields: lang.Symbol) -> lang.Rule:
    rule.fields.extend(
        [lang.Field(name=name, type=type_, value=None) for name, type_ in fields.items()]
    )
    return rule


def _ref(rule: lang.Rule) -> lang.ReferenceSymbol:
    ref = lang.ReferenceSymbol(rule.name)
    ref.rule = rule
    return ref


def _more(*symbols: lang.Symbol) -> lang.MoreSymbol:
    return lang.MoreSymbol(_seq(*symbols))


def _optional(*symbols: lang.Symbol) -> lang.OptionalSymbol:
    return lang.OptionalSymbol(_seq(*symbols))


def _separated(symbol: lang.Symbol, separator: str) -> lang.SeparatedSymbol:
    return lang.SeparatedSymbol(symbol, separator)


def _front(*rules: lang.Rule) -> lang.Front:
    return lang.Front(
        rules=list(rules),
        scan_rules=[],
    )


def _one_rule(*symbols: lang.Symbol) -> lang.Front:
    return _front(
        _rule("Root", *symbols, is_root=True),
    )


def _one_choice_rule(*choices: lang.Choice, before: list[lang.Symbol] | None = None) -> lang.Front:
    return _front(
        lang.Rule(
            is_root=True,
            name="Root",
            super_type=None,
            fields=[],
            terms=_seq(*(before if before is not None else [])),
            choices=list(choices),
        )
    )


def _record(name: str, super_type: types.RecordType | None = None, **fields) -> types.RecordType:
    record_fields = [types.Field(name=name, type=type_) for name, type_ in fields.items()]
    return types.RecordType(
        name=name,
        fields=record_fields,
        super_type=super_type,
    )


def _model(*records: types.RecordType) -> types.Model:
    return types.Model(records=list(records))


def _one_record(name: str = "Root", **fields) -> types.Model:
    return _model(_record(name, **fields))


class TestBasicTypes(unittest.TestCase):
    def test_int_field(self):
        root = _one_rule(lang.LabeledSymbol("label", lang.ReferenceSymbol("Int")))
        model = BuildTypes(root).run()
        reference = _one_record(label=types.int_type)
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_string_field(self):
        root = _one_rule(lang.LabeledSymbol("label", lang.ReferenceSymbol("String")))
        model = BuildTypes(root).run()
        reference = _one_record(label=types.string_type)
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_ident_field(self):
        root = _one_rule(lang.LabeledSymbol("label", lang.ReferenceSymbol("Ident")))
        model = BuildTypes(root).run()
        reference = _one_record(label=types.ident_type)
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_float_field(self):
        root = _one_rule(lang.LabeledSymbol("label", lang.ReferenceSymbol("Float")))
        model = BuildTypes(root).run()
        reference = _one_record(label=types.float_type)
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])


class TestBasicTypesWithLiterals(unittest.TestCase):
    def test_int_field(self):
        root = _one_rule(
            lang.StringSymbol("before"),
            lang.LabeledSymbol("label", lang.ReferenceSymbol("Int")),
            lang.StringSymbol("after"),
        )
        model = BuildTypes(root).run()
        reference = _one_record(label=types.int_type)
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_string_field(self):
        root = _one_rule(
            lang.StringSymbol("before"),
            lang.LabeledSymbol("label", lang.ReferenceSymbol("String")),
            lang.StringSymbol("after"),
        )
        model = BuildTypes(root).run()
        reference = _one_record(label=types.string_type)
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_ident_field(self):
        root = _one_rule(
            lang.StringSymbol("before"),
            lang.LabeledSymbol("label", lang.ReferenceSymbol("Ident")),
            lang.StringSymbol("after"),
        )
        model = BuildTypes(root).run()
        reference = _one_record(label=types.ident_type)
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_float_field(self):
        root = _one_rule(
            lang.StringSymbol("before"),
            lang.LabeledSymbol("label", lang.ReferenceSymbol("Float")),
            lang.StringSymbol("after"),
        )
        model = BuildTypes(root).run()
        reference = _one_record(label=types.float_type)
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])


class TestMultipleFields(unittest.TestCase):
    def test_multiple_fields(self):
        root = _one_rule(
            lang.LabeledSymbol("int_label", lang.ReferenceSymbol("Int")),
            lang.LabeledSymbol("string_label", lang.ReferenceSymbol("String")),
            lang.LabeledSymbol("ident_label", lang.ReferenceSymbol("Ident")),
            lang.LabeledSymbol("float_label", lang.ReferenceSymbol("Float")),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            int_label=types.int_type,
            string_label=types.string_type,
            ident_label=types.ident_type,
            float_label=types.float_type,
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_multiple_fields_with_literals(self):
        root = _one_rule(
            lang.StringSymbol("before"),
            lang.LabeledSymbol("int_label", lang.ReferenceSymbol("Int")),
            lang.StringSymbol("A"),
            lang.LabeledSymbol("string_label", lang.ReferenceSymbol("String")),
            lang.StringSymbol("B"),
            lang.LabeledSymbol("ident_label", lang.ReferenceSymbol("Ident")),
            lang.StringSymbol("C"),
            lang.LabeledSymbol("float_label", lang.ReferenceSymbol("Float")),
            lang.StringSymbol("after"),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            int_label=types.int_type,
            string_label=types.string_type,
            ident_label=types.ident_type,
            float_label=types.float_type,
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])


class TestMoreSymbol(unittest.TestCase):
    def test_label_outside_more(self):
        root = _one_rule(
            lang.LabeledSymbol(
                "label",
                _more(lang.ReferenceSymbol("String")),
            ),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            label=types.string_type.list(),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_label_inside_more(self):
        root = _one_rule(
            _more(
                lang.LabeledSymbol("label", lang.ReferenceSymbol("String")),
            ),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            label=types.string_type.list(),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_label_inside_nested_more(self):
        root = _one_rule(
            _more(
                _more(lang.LabeledSymbol("label", lang.ReferenceSymbol("String"))),
            ),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            label=types.string_type.list().list(),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_label_outside_nested_more(self):
        root = _one_rule(
            lang.LabeledSymbol(
                "label",
                _more(_more(lang.ReferenceSymbol("String"))),
            ),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            label=types.string_type.list().list(),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_label_between_nested_more(self):
        root = _one_rule(
            _more(
                lang.LabeledSymbol("label", _more(lang.ReferenceSymbol("String"))),
            ),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            label=types.string_type.list().list(),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_multiple_labels_inside_more(self):
        root = _one_rule(
            _more(
                lang.LabeledSymbol("label1", lang.ReferenceSymbol("String")),
                lang.LabeledSymbol("label2", lang.ReferenceSymbol("String")),
            ),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            label1=types.string_type.list(),
            label2=types.string_type.list(),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_multiple_labels_inside_nested_more_1(self):
        root = _one_rule(
            _more(
                lang.LabeledSymbol("label1", lang.ReferenceSymbol("String")),
                _more(lang.LabeledSymbol("label2", lang.ReferenceSymbol("String"))),
            ),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            label1=types.string_type.list(),
            label2=types.string_type.list().list(),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_multiple_labels_inside_nested_more_2(self):
        root = _one_rule(
            _more(
                lang.LabeledSymbol("label1", lang.ReferenceSymbol("String")),
                lang.LabeledSymbol("label2", _more(lang.ReferenceSymbol("String"))),
            ),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            label1=types.string_type.list(),
            label2=types.string_type.list().list(),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])


class TestOptionalSymbol(unittest.TestCase):
    def test_label_outside_optional(self):
        root = _one_rule(
            lang.LabeledSymbol("label", _optional(lang.ReferenceSymbol("String"))),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            label=types.string_type.optional(),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_label_inside_optional(self):
        root = _one_rule(
            _optional(lang.LabeledSymbol("label", lang.ReferenceSymbol("String"))),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            label=types.string_type.optional(),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_optional_more(self):
        root = _one_rule(
            _optional(_more(lang.LabeledSymbol("label", lang.ReferenceSymbol("String")))),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            label=types.string_type.list(),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_more_optional(self):
        root = _one_rule(
            _more(_optional(lang.LabeledSymbol("label", lang.ReferenceSymbol("String")))),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            label=types.string_type.optional().list(),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])


class TestSeparatedSymbol(unittest.TestCase):
    def test_label_outside_separated(self):
        root = _one_rule(
            lang.LabeledSymbol("label", _separated(lang.ReferenceSymbol("String"), ",")),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            label=types.string_type.list(),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_label_inside_separated(self):
        root = _one_rule(
            _separated(lang.LabeledSymbol("label", lang.ReferenceSymbol("String")), ","),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            label=types.string_type.list(),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_optional_separated(self):
        root = _one_rule(
            _optional(_separated(lang.LabeledSymbol("label", lang.ReferenceSymbol("String")), ",")),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            label=types.string_type.list(),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])


# TODO: FIELD, Choice
class TestChoice(unittest.TestCase):
    def test_choice_of_symbols(self):
        root = _one_choice_rule(
            lang.SymbolsChoice(
                _seq(lang.LabeledSymbol("str_label", lang.ReferenceSymbol("String")))
            ),
            lang.SymbolsChoice(_seq(lang.LabeledSymbol("int_label", lang.ReferenceSymbol("Int")))),
        )
        model = BuildTypes(root).run()
        reference = _one_record(
            str_label=types.string_type,
            int_label=types.int_type,
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])

    def test_choice_of_subtypes(self):
        rule_one = _with_super(
            _rule("One", lang.LabeledSymbol("str_label", lang.ReferenceSymbol("String"))), "Root"
        )
        rule_two = _with_super(
            _rule("Two", lang.LabeledSymbol("int_label", lang.ReferenceSymbol("Int"))), "Root"
        )
        root_rule = _with_choices(
            _rule("Root", is_root=True),
            lang.SymbolsChoice(_seq(_ref(rule_one))),
            lang.SymbolsChoice(_seq(_ref(rule_two))),
        )
        root = _front(
            root_rule,
            rule_one,
            rule_two,
        )
        model = BuildTypes(root).run()
        root_type = _record("Root")
        reference = _model(
            root_type,
            _record("One", super_type=root_type, str_label=types.string_type),
            _record("Two", super_type=root_type, int_label=types.int_type),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root_rule)
        self.assertIs(model.records[1].origin, rule_one)
        self.assertIs(model.records[2].origin, rule_two)

    def test_choice_of_rules(self):
        rule_one = _rule("One", lang.LabeledSymbol("str_label", lang.ReferenceSymbol("String")))
        rule_two = _rule("Two", lang.LabeledSymbol("int_label", lang.ReferenceSymbol("Int")))
        root = _one_choice_rule(
            lang.RuleChoice(rule_one),
            lang.RuleChoice(rule_two),
        )
        model = BuildTypes(root).run()
        root_type = _record("Root")
        reference = _model(
            root_type,
            _record("One", super_type=root_type, str_label=types.string_type),
            _record("Two", super_type=root_type, int_label=types.int_type),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])
        self.assertIs(model.records[1].origin, rule_one)
        self.assertIs(model.records[2].origin, rule_two)

    def test_choice_of_rules_super_has_symbols(self):
        rule_one = _rule("One", lang.LabeledSymbol("str_label", lang.ReferenceSymbol("String")))
        rule_two = _rule("Two", lang.LabeledSymbol("int_label", lang.ReferenceSymbol("Int")))
        root = _one_choice_rule(
            lang.RuleChoice(rule_one),
            lang.RuleChoice(rule_two),
            before=[lang.LabeledSymbol("super_label", lang.ReferenceSymbol("String"))],
        )
        model = BuildTypes(root).run()
        root_type = _record("Root", super_label=types.string_type)
        reference = _model(
            root_type,
            _record("One", super_type=root_type, str_label=types.string_type),
            _record("Two", super_type=root_type, int_label=types.int_type),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root.rules[0])
        self.assertIs(model.records[1].origin, rule_one)
        self.assertIs(model.records[2].origin, rule_two)


class TestField(unittest.TestCase):
    def test_fields(self):
        rule = _with_fields(
            _rule("Test"),
            str_label=lang.ReferenceSymbol("String"),
        )
        model = BuildTypes(_front(rule)).run()
        reference = _model(
            _record("Test", str_label=types.string_type),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, rule)

    def test_fields_and_symbols(self):
        root = _rule(
            "Root",
            lang.LabeledSymbol("label", lang.ReferenceSymbol("String")),
        )
        _with_fields(
            root,
            int_label=lang.ReferenceSymbol("Int"),
        )
        model = BuildTypes(_front(root)).run()
        reference = _model(
            _record("Root", int_label=types.int_type, label=types.string_type),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root)

    def test_fields_with_super_types(self):
        rule_one = _rule("One", lang.LabeledSymbol("str_label", lang.ReferenceSymbol("String")))
        rule_two = _rule("Two", lang.LabeledSymbol("int_label", lang.ReferenceSymbol("Int")))
        root = _with_choices(
            _rule("Root"),
            lang.RuleChoice(rule_one),
            lang.RuleChoice(rule_two),
        )
        _with_fields(
            root,
            str_label=lang.ReferenceSymbol("String"),
        )
        model = BuildTypes(_front(root)).run()
        root_type = _record("Root", str_label=types.string_type)
        reference = _model(
            root_type,
            _record("One", super_type=root_type),
            _record("Two", super_type=root_type, int_label=types.int_type),
        )
        self.assertEqual(model, reference)
        self.assertIs(model.records[0].origin, root)


class TestInvalidSource(unittest.TestCase):
    def test_missing_label(self):
        root = _one_rule(
            lang.ReferenceSymbol("String"),
        )
        with self.assertRaises(MissingLabelError):
            BuildTypes(root).run()

    def test_label_outside_more_with_multiple_symbols(self):
        root = _one_rule(
            lang.LabeledSymbol(
                "label", _more(lang.ReferenceSymbol("String"), lang.ReferenceSymbol("String"))
            ),
        )
        with self.assertRaises(DuplicateLabelError):
            BuildTypes(root).run()

    def test_label_outside_optional_with_multiple_symbols(self):
        root = _one_rule(
            lang.LabeledSymbol(
                "label",
                _optional(
                    lang.ReferenceSymbol("String"),
                    lang.ReferenceSymbol("String"),
                ),
            )
        )
        with self.assertRaises(DuplicateLabelError):
            BuildTypes(root).run()

    def test_multiple_labels(self):
        root = _one_rule(
            lang.LabeledSymbol(
                "label1", lang.LabeledSymbol("label2", lang.ReferenceSymbol("String"))
            ),
        )
        with self.assertRaises(DoubleLabelingError):
            BuildTypes(root).run()

    def test_multiple_labels_with_more(self):
        root = _one_rule(
            lang.LabeledSymbol(
                "label1", _more(lang.LabeledSymbol("label2", lang.ReferenceSymbol("String")))
            ),
        )
        with self.assertRaises(DoubleLabelingError):
            BuildTypes(root).run()

    def test_field_type_mismatch(self):
        root = _rule(
            "Root",
            lang.LabeledSymbol("label", lang.ReferenceSymbol("String")),
        )
        _with_fields(
            root,
            label=lang.ReferenceSymbol("Int"),
        )
        with self.assertRaises(ValueError):
            BuildTypes(_front(root)).run()
