from collections import Counter
from collections.abc import Iterable

import pyfront.grammar.model as gm
import pyfront.lang.model as lang
from pyfront.lang.walk import walk_front
from pyfront.support.errors import AstError
from pyfront.types.model import (
    ContainerType,
    ListType,
    Model,
    OptionalType,
    RecordType,
    TupleType,
    Type,
    bool_type,
    int_type,
    none_type,
)


class DeeplyNestedRecordError(AstError):
    """Exception for deeply nested records in the AST."""

    def __init__(self, rule: lang.Rule):
        super().__init__(rule, f"deeply nested records not supported: {rule.name}")


class DoubleLabelingError(AstError):
    """Exception for labeling a symbol twice in the AST."""

    def __init__(self, symbol: lang.Symbol):
        super().__init__(symbol, "nesting labels is not allowed")


class MissingLabelError(AstError):
    """Exception for missing labels in the AST."""

    def __init__(self, symbol: lang.Symbol):
        super().__init__(symbol, "missing label")


class DuplicateLabelError(AstError):
    """Exception for duplicate labels in the AST."""

    def __init__(self, node: object, *labels: str):
        if len(labels) == 1:
            super().__init__(node, f"duplicate label found: {labels[0]}")
        else:
            labels_str = ", ".join(labels)
            super().__init__(node, f"duplicate labels found: {labels_str}")


_UNLABELED_CHOICE = object()


class BuildTypes:
    def __init__(self, front: lang.Front) -> None:
        self.front = front
        self.types = Model()
        self.record_stack: list[RecordType | None] = [None]
        self.container_stack: list[type[ContainerType]] = []
        self.current_label: str | None = None
        self.sequence_labels: list[str | None] = []
        self.found_keyword: bool = False
        self.default_value: gm.Expression | None = None

    def _new_field(self, name: str, type_: Type) -> lang.Field:
        if self.record_stack[-1] is None:
            raise ValueError("No record in stack to add field to")
        for container in reversed(self.container_stack):
            type_ = container.make(inner_type=type_)
        return self.record_stack[-1].new_field(name, type_)

    def pre_rule(self, rule: lang.Rule) -> None:
        if rule.super_type is not None:
            if len(self.record_stack) > 1:
                raise DeeplyNestedRecordError(rule)

            record = self.types.new_record(rule.name, self.types.get_type_by_name(rule.super_type))
        else:
            record = self.types.new_record(rule.name, self.record_stack[-1])
        record.origin = rule
        rule.type = record
        self.record_stack.append(record)
        self.sequence_labels = []

    def pre_field(self, field: lang.Field) -> None:
        self.current_label = field.name
        self.default_value = field.value

    def pre_labeled_symbol(self, symbol) -> None:
        if self.current_label is not None:
            raise DoubleLabelingError(symbol)
        self.current_label = symbol.label
        self.found_keyword = False

    def pre_more_symbol(self, symbol) -> None:
        self.container_stack.append(ListType)

    def pre_optional_symbol(self, symbol) -> None:
        self.container_stack.append(OptionalType)

    def pre_separated_symbol(self, symbol) -> None:
        self.container_stack.append(ListType)

    def post_string_symbol(self, symbol) -> None:
        symbol.type = none_type

    def pre_symbols_choice(self, choice) -> None:
        if (
            len(choice.symbols.symbols) == 1
            and isinstance(choice.symbols.symbols[0], lang.ReferenceSymbol)
            and self.current_label is None
        ):
            self.current_label = _UNLABELED_CHOICE

    def post_reference_symbol(self, symbol) -> None:
        symbol.type = self.types.get_type_by_name(symbol.name)
        if self.current_label is None:
            raise MissingLabelError(symbol)
        if self.current_label == _UNLABELED_CHOICE:
            return

        self.sequence_labels.append(self.current_label)
        field = self._new_field(self.current_label, symbol.type)
        if self.default_value is not None:
            field.default = self.default_value
            self.default_value = None
        self.found_keyword = True

    def post_symbols_choice(self, choice) -> None:
        if self.current_label is _UNLABELED_CHOICE:
            self.current_label = None

    def post_labeled_symbol(self, symbol) -> None:
        if not self.found_keyword:
            self.sequence_labels.append(symbol.label)
            self._new_field(self.current_label, bool_type)
            symbol.type = bool_type
        else:
            symbol.type = symbol.symbol.type
        self.current_label = None

    def post_separated_symbol(self, symbol) -> None:
        self.container_stack.pop()
        symbol.type = symbol.symbol.type.list()

    def into_symbol_sequence(self, symbol_sequence) -> Iterable[None]:
        outer_labels = self.sequence_labels
        self.sequence_labels = []
        yield
        typed_syms = [sym for sym in symbol_sequence.symbols if sym.type is not none_type]
        if len(typed_syms) == 0:
            symbol_sequence.type = none_type
        elif len(typed_syms) == 1 and len(self.sequence_labels) == 0:
            symbol_sequence.type = typed_syms[0].type
        elif len(typed_syms) == 1 and isinstance(typed_syms[0].type, TupleType):
            assert len(self.sequence_labels) == len(typed_syms[0].type.fields), (
                "Mismatch between symbols and labels for tuple type"
            )
            symbol_sequence.type = typed_syms[0].type
        else:
            counts = Counter(self.sequence_labels)
            duplicates = [label for label, count in counts.items() if count > 1]
            if duplicates:
                raise DuplicateLabelError(symbol_sequence, *duplicates)

            assert len(typed_syms) == len(self.sequence_labels), (
                "Mismatch between symbols and labels"
            )
            map = {label: sym.type for label, sym in zip(self.sequence_labels, typed_syms)}
            symbol_sequence.type = self.types.new_tuple(map)
        self.sequence_labels = [*outer_labels, *self.sequence_labels]

    def post_group_symbol(self, symbol) -> None:
        symbol.type = symbol.symbols.type

    def post_more_symbol(self, symbol) -> None:
        self.container_stack.pop()
        if symbol.symbols.type is none_type:
            symbol.type = int_type
        else:
            symbol.type = symbol.symbols.type.list()

    def post_optional_symbol(self, symbol) -> None:
        self.container_stack.pop()
        if symbol.symbols.type is none_type:
            symbol.type = bool_type
        else:
            symbol.type = symbol.symbols.type.optional()

    def post_field(self, field: lang.Field) -> None:
        self.current_label = None

    def post_rule(self, rule: lang.Rule) -> None:
        self.record_stack.pop()

    def run(self) -> Model:
        walk_front(self.front, self)
        self.types.finalize()
        return self.types
