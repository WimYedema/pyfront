import pyfront.grammar.model as gm
from pyfront.lang.model import Field, Front, Rule
from pyfront.lang.walk import walk_front
from pyfront.types.model import (
    ContainerType,
    ListType,
    Model,
    OptionalType,
    RecordType,
    Type,
    bool_type,
)


class BuildTypes:
    def __init__(self, front: Front) -> None:
        self.front = front
        self.types = Model()
        self.record_stack: list[RecordType | None] = [None]
        self.container_stack: list[type[ContainerType]] = []
        self.current_label: str | None = None
        self.found_keyword: bool = False
        self.default_value: gm.Expression | None = None

    def _new_field(self, name: str, type_: Type) -> Field:
        if self.record_stack[-1] is None:
            raise ValueError("No record in stack to add field to")
        for container in reversed(self.container_stack):
            type_ = container.make(inner_type=type_)
        return self.record_stack[-1].new_field(name, type_)

    def pre_rule(self, rule: Rule) -> None:
        if rule.is_ref:
            return
        if rule.super_type is not None:
            if len(self.record_stack) > 1:
                raise ValueError(f"{rule.name}: nested record with super types are not supported")

            record = self.types.new_record(rule.name, self.types.get_type_by_name(rule.super_type))
        else:
            record = self.types.new_record(rule.name, self.record_stack[-1])
        self.record_stack.append(record)

    def pre_field(self, field: Field) -> None:
        self.current_label = field.name
        self.default_value = field.value

    def pre_labeled_symbol(self, symbol) -> None:
        if self.current_label is not None:
            raise ValueError("Nested labeled symbols are not supported")
        self.current_label = symbol.label
        self.found_keyword = False

    def pre_group_symbol(self, symbol) -> None:
        if symbol.multiple:
            self.container_stack.append(ListType)
        elif symbol.optional:
            self.container_stack.append(OptionalType)

    def pre_separated_symbol(self, symbol) -> None:
        self.container_stack.append(ListType)

    def post_keyword_symbol(self, symbol) -> None:
        field = self._new_field(self.current_label, self.types.get_type_by_name(symbol.keyword))
        if self.default_value is not None:
            field.default = self.default_value
            self.default_value = None
        self.found_keyword = True

    def post_labeled_symbol(self, symbol) -> None:
        if not self.found_keyword:
            self._new_field(self.current_label, bool_type)
        self.current_label = None

    def post_separated_symbol(self, symbol) -> None:
        self.container_stack.pop()

    def post_group_symbol(self, symbol) -> None:
        if symbol.multiple or symbol.optional:
            self.container_stack.pop()

    def post_field(self, field: Field) -> None:
        self.current_label = None

    def post_rule(self, rule: Rule) -> None:
        if rule.is_ref:
            return
        self.record_stack.pop()

    def run(self) -> Model:
        walk_front(self.front, self)
        self.types.finalize()
        return self.types
