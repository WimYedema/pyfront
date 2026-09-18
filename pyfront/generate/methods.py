import re

import pyfront.lang.model as lang
import pyfront.types.model as types
from pyfront.generate.emitter import Emitter
from pyfront.lang.walk import walk_symbol


class GetFields:
    def __init__(self) -> None:
        self.fields = []

    def post_reference_symbol(self, symbol: lang.ReferenceSymbol) -> None:
        self.fields.append(symbol.label)

    @classmethod
    def from_symbols(cls, *symbols: lang.Symbol) -> list[str]:
        instance = cls()
        for sym in symbols:
            walk_symbol(sym, instance)
        return instance.fields


class StrMethod(types.Method):
    _record: types.RecordType

    def __init__(self, record: types.RecordType) -> None:
        self._record = record
        self._need_space = False
        super().__init__(name="__str__", return_type=types.string_type, parameters=[])

    def _generate_list_str(
        self,
        emitter: Emitter,
        accessor: str,
        *symbols: lang.Symbol,
        separator: str | None = None,
    ) -> None:
        fields = GetFields.from_symbols(*symbols)
        field_str = ", ".join([accessor.format(accessor=field) for field in fields])
        item_str = ", ".join([f"{field}_item" for field in fields])
        if self._need_space:
            emitter.emit("result += _spacing_")
            self._need_space = False
        emitter.emit(f"_iter_syms = list(zip({field_str}))")
        emitter.emit("_last_index = len(_iter_syms) - 1")
        emitter.emit(f"for _index, ({item_str},) in enumerate(_iter_syms):")
        emitter.indent()
        for sym in symbols:
            self._generate_term_str(sym, emitter, "{accessor}_item")
        emitter.emit("if _index!=_last_index:").indent()
        if self._need_space:
            emitter.emit("result += _spacing_")
        if separator is not None:
            emitter.emit(f'result += "{separator}" + _spacing_')
        self._need_space = False
        emitter.dedent()
        emitter.dedent()

    def _generate_term_str(
        self, term: lang.Symbol, emitter: Emitter, accessor: str = "{accessor}"
    ) -> None:
        match term:
            case lang.LabeledSymbol(label=_, symbol=symbol):
                self._generate_term_str(symbol, emitter, accessor)
            case lang.StringSymbol(value=value):
                if not self._need_space or re.match(r"^[\(\)\[\]\{\}]+$", value) is not None:
                    # parens and other enclosures have no spacing
                    emitter.emit(f'result += "{value}"')
                    self._need_space = False
                else:
                    emitter.emit(f'result += _spacing_ + "{value}"')
                    self._need_space = True

            case lang.ReferenceSymbol(name=_):
                if self._need_space:
                    emitter.emit("result += _spacing_")
                if isinstance(term.rule, lang.ScanRule):
                    value = accessor.format(accessor=term.label)
                    emitter.emit(f"result += {repr(term.rule.format)}.format(value={value})")
                else:
                    emitter.emit(f"result += str({accessor.format(accessor=term.label)})")
                self._need_space = True
            case lang.SeparatedSymbol(symbol=symbol, separator=separator):
                self._generate_list_str(emitter, accessor, symbol, separator=separator)
            case lang.GroupSymbol(symbols=symbols):
                for sym in symbols.symbols:
                    self._generate_term_str(sym, emitter, accessor)
            case lang.OptionalSymbol(symbols=symbols):
                if term.type is types.bool_type:
                    emitter.emit(f"if {accessor.format(accessor=term.label)}:")
                else:
                    emitter.emit(f"if {accessor.format(accessor=term.label)} is not None:")
                emitter.indent()
                for sym in symbols.symbols:
                    self._generate_term_str(sym, emitter, accessor)
                emitter.dedent()
            case lang.MoreSymbol(symbols=symbols, optional=_):
                self._generate_list_str(emitter, accessor, *symbols.symbols)

            case _:
                raise NotImplementedError(f"String generation not implemented for {type(term)}")

    def generate_body(self, emitter: Emitter) -> None:
        if self._record.origin is None:
            raise ValueError("Record has no origin rule associated with it")

        emitter.emit('_spacing_ = " "')
        for field in self._record.fields:
            emitter.emit(f"{field.name} = self.{field.name}")
        emitter.emit('result = ""')
        for term in self._record.origin.terms.symbols:
            self._generate_term_str(term, emitter)
        emitter.emit("return result.lstrip()")


def generate_str_method(model: types.Model) -> None:
    for record in model.records:
        _generate_str_method(record)


def _generate_str_method(record: types.RecordType) -> None:
    if any(method.name == "__str__" for method in record.methods):
        return
    record.methods.append(StrMethod(record))
