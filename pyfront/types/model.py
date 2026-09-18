from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import ClassVar

import pyfront.lang.model as lang


@dataclass
class Type:
    name: str

    def is_subtype_of(self, other: Type) -> bool:
        return self == other

    def list(self) -> Type:
        return ListType.make(inner_type=self)

    def optional(self) -> Type:
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
none_type = BuiltinType("None")

builtin_type = {
    "Ident": ident_type,
    "String": string_type,
    "Int": int_type,
    "Float": float_type,
    "Bool": bool_type,
    "None": none_type,
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

    @classmethod
    def make(cls, inner_type: Type) -> ContainerType:
        if isinstance(inner_type, (OptionalType, ListType)):
            return inner_type
        return super().make(inner_type=inner_type)


@dataclass
class ListType(ContainerType):
    def is_subtype_of(self, other: Type) -> bool:
        if isinstance(other, ListType):
            return self.inner_type.is_subtype_of(other.inner_type)
        return False

    def optional(self) -> Type:
        return self


@dataclass
class Field:
    name: str
    type: Type
    default: lang.Expression | None = None

    def __str__(self) -> str:
        value_str = f" = {self.default}" if self.default is not None else ""
        return f"{self.name}: {self.type.name}{value_str}"


@dataclass
class CompoundType(Type):
    fields: list[Field] = field(default_factory=list)

    def iter_fields(self) -> Iterable[Field]:
        """Iterate over fields."""
        yield from self.fields

    def is_subtype_of(self, other: Type) -> bool:
        return self == other

    def find_field(self, name: str) -> Field | None:
        for fld in self.fields:
            if fld.name == name:
                return fld
        return None

    def new_field(self, name: str, type_: Type) -> Field:
        field = Field(name=name, type=type_)
        self.add_field(field)
        return field

    def add_field(self, field: Field) -> None:
        self.fields.append(field)


@dataclass
class Method:
    name: str
    return_type: Type = field(default_factory=lambda: none_type)
    parameters: list[Field] = field(default_factory=list)

    def __str__(self) -> str:
        params_str = ", ".join(str(param) for param in self.parameters)
        return f"Method {self.name}({params_str}) -> {self.return_type.name}"


@dataclass
class RecordType(CompoundType):
    super_type: RecordType | None = None
    methods: list[Method] = field(default_factory=list)
    origin: lang.Rule | None = field(default=None, compare=False)

    def iter_fields(self) -> Iterable[Field]:
        """Iterate over fields of this record and its super types."""
        if self.super_type is not None:
            yield from self.super_type.iter_fields()
        yield from super().iter_fields()

    def is_subtype_of(self, other: Type) -> bool:
        if not isinstance(other, RecordType):
            return False

        current: RecordType | None = self
        while current is not None:
            if current == other:
                return True
            current = current.super_type
        return False

    def find_field(self, name: str, *, into_super: bool = True) -> Field | None:
        fld = super().find_field(name)
        if fld is not None:
            return fld
        if into_super and self.super_type is not None:
            return self.super_type.find_field(name, into_super=into_super)
        return None

    def find_method(self, name: str, *, into_super: bool = True) -> Method | None:
        for mth in self.methods:
            if mth.name == name:
                return mth
        if into_super and self.super_type is not None:
            return self.super_type.find_method(name, into_super=into_super)
        return None

    def __str__(self) -> str:
        super_str = f"({self.super_type.name})" if self.super_type else ""
        fields_str = ", ".join(str(field) for field in self.fields)
        return f"Record {self.name}{super_str} {{ {fields_str} }}"

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


@dataclass
class TupleType(CompoundType):
    tuple_counter: ClassVar[int] = 0

    def __post_init__(self) -> None:
        TupleType.tuple_counter += 1

    def __str__(self) -> str:
        fields_str = ", ".join(str(field) for field in self.fields)
        return f"Tuple {self.name} {{ {fields_str} }}"

    @classmethod
    def make(cls, entries: dict[str, Type]) -> TupleType:
        fields = []
        for name, type_ in entries.items():
            if not isinstance(type_, TupleType):
                fields.append(Field(name=name, type=type_))
            else:
                for fld in type_.fields:
                    fields.append(Field(name=fld.name, type=fld.type))
        tuple_type = cls(name=f"Tuple{TupleType.tuple_counter}", fields=fields)
        return tuple_type

    def list(self) -> Type:
        if len(self.fields) == 1:
            return self.fields[0].type.list()
        return TupleType.make({fld.name: fld.type.list() for fld in self.fields})

    def optional(self) -> Type:
        if len(self.fields) == 1:
            return self.fields[0].type.optional()
        return TupleType.make({fld.name: fld.type.optional() for fld in self.fields})


@dataclass
class Model:
    records: list[RecordType] = field(default_factory=list)

    def finalize(self) -> None:
        for record in self.records:
            record.finalize()
        # topologically sort records such that super-types come first
        seen = set()
        sorted_records = []

        def visit(record: RecordType) -> None:
            if record.name in seen:
                return
            if record.super_type is not None:
                visit(record.super_type)
            seen.add(record.name)
            sorted_records.append(record)

        for record in self.records:
            visit(record)

        self.records = sorted_records

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

    def new_tuple(self, entries: dict[str, Type]) -> TupleType:
        tuple_type = TupleType.make(entries=entries)
        return tuple_type

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
