from collections.abc import Iterable
from typing import Self

from inflection import camelize, underscore

import pyfront.grammar.model as gm
import pyfront.types.model as types
from pyfront.generate.expression import gen_expression
from pyfront.generate.parse_table import PopulateParseTable
from pyfront.grammar.grammar_builder import GrammarBuilder
from pyfront.grammar.inlining import Inlining
from pyfront.grammar.left_factoring import LeftFactoring
from pyfront.lang.model import Front

from ._base import GeneratorBase
from .emitter import Emitter


def sort_terminals(terminals: Iterable[gm.Terminal]) -> Iterable[gm.Terminal]:
    """Sort terminals by length of their value, then alphabetically."""
    return sorted(terminals, key=lambda t: t.prio)


class GenerateParser(GeneratorBase):
    def __init__(self, front: Front, emitter: Emitter) -> None:
        super().__init__(emitter)
        self.front = front

    def generate_non_terminals(self) -> None:
        self.emit("class NonTerminals(_NonTerminals):").indent()
        for nt in self.grammar.non_terminals:
            self.emit(f"{underscore(nt.name).upper()} = auto()")
        self.dedent().emit()

    def generate_terminals(self) -> None:
        self.emit("class Terminals(_Terminals):").indent()
        for term in self.grammar.terminals:
            self.emit(f"{term.name} = auto()")
        self.emit("_EOF = auto()")
        self.dedent().emit()

    def generate_token_map(self) -> None:
        self.emit("LiteralText = {").indent()
        for term in sort_terminals(t for t in self.grammar.terminals if t.type == types.none_type):
            self.emit(f"Terminals.{term.name}: {term.value},")
        self.dedent().emit("}")

        self.emit("TokenRegex = {").indent()
        for term in sort_terminals(t for t in self.grammar.terminals if t.type != types.none_type):
            self.emit(f"Terminals.{term.name}: {term.value},")
        self.dedent().emit("}")

    def generate_whitespace_map(self) -> None:
        self.emit("""
            WhitespaceRegexs = {
                r"\\s+", # whitespace
                r"//.*",  # single-line comment
            }
            """)

    def generate_lexer_code(self) -> None:
        self.emit("class Tokenizer:")
        self.indent()
        self.generate_token_map()
        self.generate_whitespace_map()
        self.dedent()

    def generate_constructor(self, rv: gm.RuleValue) -> str:
        match rv:
            case gm.NoValue(stack=stack):
                if len(stack) == 0:
                    return "_undefined"
                return str(stack[0])

            case gm.ExprValue(expression=expression):
                return gen_expression(expression)

            case gm.ConstructValue(construct_type=construct_type, stack=stack):
                kwargs = {}
                field_map = {}
                for param in stack:
                    assert param.type == types.none_type or param.name is not None, (
                        "Parameter name should not be None when generating constructor"
                    )
                    field_map[param.name] = param
                    kwargs[param.name] = param.name

                match construct_type:
                    case types.ListType():
                        args = []
                        if "head" in kwargs:
                            args.append(kwargs["head"])
                        if "tail" in kwargs:
                            if not isinstance(field_map["tail"].type, types.ListType):
                                raise ValueError("Expected 'tail' to be of type ListType")
                            args.append(f"*{kwargs['tail']}")
                        args_str = ", ".join(args)
                        return f"[{args_str}]"
                    case types.TupleType():
                        args = [v for v in kwargs.values()]
                        args_str = ", ".join(args)
                        return f"({args_str},)"
                    case types.OptionalType():
                        assert not kwargs, "OptionalType should not have any keyword arguments"
                        return "None"
                    case _:
                        args = [f"{k}={v}" for k, v in kwargs.items()]
                        args_str = ", ".join(args)
                        return f"model.{construct_type.name}({args_str})"

    def generate_rule_code(self) -> None:
        for index, rule in enumerate(self.grammar.rules):
            args = []
            args += [f", {label}: object" for label in rule.arguments]
            if args:
                args.insert(0, ", *")
            terms = []
            for term in rule.terms:
                if isinstance(term, gm.TerminalTerm):
                    term_text = "Terminals." + term.name
                else:
                    term_text = "NonTerminals." + underscore(term.name).upper()

                terms.append(term_text)

            constructor = self.generate_constructor(rule.value)
            argument_names = [f'"{label}"' for label in rule.arguments]
            argument_names_str = ", ".join(argument_names)
            self.emit(f"""
                # {str(rule)}
                class Rule{index}{camelize(rule.nt.name)}:
                    terms = [{", ".join(terms)}]
                    argument_names = [{argument_names_str}]

                    def build(self{"".join(args)}) -> object:
                        return {constructor}

                """)

    def generate_parse_table(self) -> None:
        parse_table = PopulateParseTable(self.grammar).compute()
        self.emit("parse_table = {").indent()
        terminals = {t.name for t in self.grammar.terminals}
        terminals.add("_EOF")
        for nt in self.grammar.non_terminals:
            self.emit(f"NonTerminals.{underscore(nt.name).upper()}: {{").indent()
            for term, rule in parse_table[nt].items():
                if term in terminals:
                    self.emit(f"Terminals.{term}: {rule},")
                else:
                    self.emit(f"NonTerminals.{underscore(term).upper()}: {rule},")
            self.dedent().emit("},")
        self.dedent().emit("}")

    def generate_rules_list(self) -> str:
        self.emit("rules = [")
        for i, rule in enumerate(self.grammar.rules):
            self.emit(f"    Rule{i}{camelize(rule.nt.name)}(),")
        self.emit("]")

    def generate_grammar_class(self) -> None:
        self.emit("class LlGrammar:")
        self.indent()
        self.emit(f"start = NonTerminals.{underscore(self.grammar.start.name).upper()}")
        self.generate_rules_list()
        self.generate_parse_table()
        self.dedent()

    def generate_code(self) -> None:
        self.emit("""
            from enum import auto

            from pyfront.support.lexer import Lexer as _Lexer
            from pyfront.support.ll_parser import LlParser as _LlParser
            from pyfront.support.ll_parser import NonTerminals as _NonTerminals
            from pyfront.support.ll_parser import Terminals as _Terminals
            from pyfront.support.ll_parser import undefined as _undefined

            from . import model

            """)

        self.generate_terminals()
        self.generate_lexer_code()
        self.generate_non_terminals()
        self.generate_rule_code()
        self.generate_grammar_class()

        self.emit("""
            def parse(text: str) -> object:
                parser = _LlParser(LlGrammar())
                lexer = _Lexer(Tokenizer, text, eof_token=Terminals._EOF)
                return parser.parse(lexer)
            """)

    def run(self) -> Self:
        self.grammar = GrammarBuilder().build(self.front)
        Inlining(self.grammar).compute()
        self.grammar = LeftFactoring(self.grammar).compute()

        self.generate_code()
        return self
