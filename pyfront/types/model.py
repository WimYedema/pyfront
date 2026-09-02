from __future__ import annotations

from dataclasses import dataclass, field
from textwrap import indent

import pyfront.grammar.model as gm


@dataclass
class Type:
    name: str

    def is_subtype_of(self, other: Type) -> bool:
        return self == other

    def list(self) -> ListType:
        return ListType.make(inner_type=self)

    def optional(self) -> OptionalType:
        return OptionalType.make(inner_type=self)

    def __str__(self) -> str:
        return self.name


@dataclass
class BuiltinType(Type):
    pass


ident_type = BuiltinType("Ident")
string_type = BuiltinType("String")
int_type = BuiltinType("Int")
float_type = BuiltinType("Float")
bool_type = BuiltinType("Bool")

builtin_type = {
    "Ident": ident_type,
    "String": string_type,
    "Int": int_type,
    "Float": float_type,
    "Bool": bool_type,
}


@dataclass
class ContainerType(Type):
    inner_type: Type

    @classmethod
    def make(cls, inner_type: Type) -> ContainerType:
        return cls(inner_type=inner_type, name=f"{cls.__name__.lower()}[{inner_type.name}]")


@dataclass
class OptionalType(ContainerType):
    def is_subtype_of(self, other: Type) -> bool:
        if isinstance(other, OptionalType):
            return self.inner_type.is_subtype_of(other.inner_type)
        return False


@dataclass
class ListType(ContainerType):
    def is_subtype_of(self, other: Type) -> bool:
        if isinstance(other, ListType):
            return self.inner_type.is_subtype_of(other.inner_type)
        return False


@dataclass
class Field:
    name: str
    type: Type
    default: gm.Expression | None = None

    def __str__(self) -> str:
        value_str = f" = {self.default}" if self.default is not None else ""
        return f"{self.name}: {self.type.name}{value_str}"


@dataclass
class RecordType(Type):
    super_type: RecordType | None = None
    fields: list[Field] = field(default_factory=list)

    def is_subtype_of(self, other: Type) -> bool:
        if not isinstance(other, RecordType):
            return False

        current: RecordType | None = self
        while current is not None:
            if current == other:
                return True
            current = current.super_type
        return False

    def find_field(self, name: str) -> Field | None:
        for fld in self.fields:
            if fld.name == name:
                return fld
        if self.super_type is not None:
            return self.super_type.find_field(name)
        return None

    def new_field(self, name: str, type_: Type) -> Field:
        field = Field(name=name, type=type_)
        self.add_field(field)
        return field

    def add_field(self, field: Field) -> None:
        self.fields.append(field)

    def finalize(self) -> None:
        field_map: dict[str, list[Field]] = {}
        for fld in self.fields:
            if self.super_type is None or self.super_type.find_field(fld.name) is None:
                field_map.setdefault(fld.name, []).append(fld)

        final_fields: list[Field] = []
        for name, fields in field_map.items():
            if len(fields) == 1:
                final_fields.append(fields[0])
            else:
                common_type = fields[0].type
                default_value = fields[0].default
                for fld in fields[1:]:
                    if fld.default is not None:
                        if default_value is None:
                            default_value = fld.default
                        elif default_value != fld.default:
                            raise ValueError(
                                f"Field {name} has conflicting default values: {default_value} and {fld.default}"
                            )
                    if common_type.is_subtype_of(fld.type):
                        common_type = fld.type
                    elif not fld.type.is_subtype_of(common_type):
                        raise ValueError(
                            f"Field {name} has conflicting types: {common_type.name} and {fld.type.name}"
                        )
                final_fields.append(Field(name=name, type=common_type, default=default_value))

        self.fields = final_fields

    def __str__(self) -> str:
        super_str = f"({self.super_type.name})" if self.super_type else ""
        fields_str = ", ".join(str(field) for field in self.fields)
        fields_str = indent(fields_str, "    ")
        return f"Record {self.name}{super_str}:\n{{{fields_str}\n}}"


@dataclass
class Model:
    records: list[RecordType] = field(default_factory=list)

    def finalize(self) -> None:
        for record in self.records:
            record.finalize()

    def new_record(self, name: str, super_type: RecordType | None = None) -> RecordType:
        existing = self.find_type_by_name(name)
        if existing is not None:
            if not isinstance(existing, RecordType):
                raise ValueError(f"Type with name {name} already exists and is not a record")
            if existing.super_type is not None:
                raise ValueError(f"Record with name {name} already exists and has a super type")
            existing.super_type = super_type
            return existing

        record = RecordType(name=name, super_type=super_type)
        self.add_record(record)
        return record

    def add_record(self, record: RecordType) -> None:
        self.records.append(record)

    def find_type_by_name(self, name: str) -> Type | None:
        if name in builtin_type:
            return builtin_type[name]
        for record in self.records:
            if record.name == name:
                return record
        return None

    def get_type_by_name(self, name: str) -> Type | None:
        record = self.find_type_by_name(name)
        if record is not None:
            return record
        return self.new_record(name)

    def __str__(self) -> str:
        return "\n".join(str(record) for record in self.records)
