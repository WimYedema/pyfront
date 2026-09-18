import unittest

from pyfront.generate.emitter import StringEmitter
from pyfront.generate.methods import StrMethod, generate_str_method
from pyfront.generate.model import GenerateModel


class TestStrMethod(unittest.TestCase):
    def parse_source(self, source: str):
        from pyfront.lang.grammar import Tokenizer, TokenType, parse_front
        from pyfront.lang.parser import Parser
        from pyfront.support.lexer import Lexer
        from pyfront.symtab import SymbolTable
        from pyfront.types.types_builder import build_types

        parser = Parser(Lexer(Tokenizer(), source, eof_token=TokenType._EOF))
        front = parse_front(parser)
        SymbolTable.populate(front)
        return build_types(front)

    def inject_methods(self, cls, source: str):
        namespace = {}
        try:
            exec(source, namespace)
        except:
            print(source)
            raise
        for k, v in namespace.items():
            setattr(cls, k, v)

    def run_test(self, cls):
        model = self.parse_source(f"{cls.__name__} ::= {cls.front};")
        generate_str_method(model)
        code: dict[str, StrMethod] = {
            record.name: record.find_method("__str__") for record in model.records
        }
        emitter = StringEmitter()
        GenerateModel(model, emitter).gen_one_method(code[cls.__name__])
        self.inject_methods(cls, emitter.get_content())
        self.assertEqual(str(cls()), cls.reference)

    def test_int_field_access(self):
        class Root:
            field: int = 42
            front = '"(" field: Int ")"'
            reference = "(42)"

        self.run_test(Root)

    def test_float_field_access(self):
        class Root:
            field: float = 3.14
            front = "field: Float"
            reference = "3.14"

        self.run_test(Root)

    def test_string_field_access(self):
        class Root:
            field: str = "Foo"
            front = "field: String"
            reference = '"Foo"'

        self.run_test(Root)

    def test_ident_field_access(self):
        class Root:
            field: str = "Foo"
            front = "field: Ident"
            reference = "Foo"

        self.run_test(Root)

    def test_field_access_with_grouping(self):
        class Root:
            field: list[int] = [1, 2, 3]
            front = 'field: ( "(" {Int} ")" )'
            reference = "(1 2 3)"

        self.run_test(Root)

    def test_list_field_access(self):
        class Root:
            field: list[int] = [1, 2, 3]
            front = '"(" field: {Int} ")"'
            reference = "(1 2 3)"

        self.run_test(Root)

    def test_separated_list_field_access(self):
        class Root:
            field: list[int] = [1, 2, 3]
            front = '"(" field: Int / "," ")"'
            reference = "(1 , 2 , 3)"

        self.run_test(Root)

    def test_optional_absent_field_access(self):
        class Root:
            field: int | None = None
            front = "field: [Int]"
            reference = ""

        self.run_test(Root)

    def test_optional_present_field_access(self):
        class Root:
            field: int | None = 42
            front = "field: [Int]"
            reference = "42"

        self.run_test(Root)

    def test_optional_absent_terminal_access(self):
        class Root:
            field: bool = False
            front = 'field: ["Foo"]'
            reference = ""

        self.run_test(Root)

    def test_optional_present_terminal_access(self):
        class Root:
            field: bool = True
            front = 'field: ["Foo"]'
            reference = "Foo"

        self.run_test(Root)

    def test_combinations(self):
        class Root:
            field1: int = 42
            field2: str | None = "Foo"
            field3: str | None = None
            field4: list[int] = [1, 2, 3]
            front = (
                '"(" field1: Int "," [field2: String] "," [field3: String] "," field4: {Int} ")"'
            )
            reference = '(42 , "Foo" , , 1 2 3)'

        self.run_test(Root)
