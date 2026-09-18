from pathlib import Path

from pyfront.generate.emitter import FolderEmitter
from pyfront.generate.methods import generate_str_method
from pyfront.generate.model import GenerateModel
from pyfront.generate.parser import GenerateParser
from pyfront.generate.report import report
from pyfront.lang.grammar import Tokenizer, TokenType, parse_front
from pyfront.lang.parser import Parser
from pyfront.support.lexer import Lexer
from pyfront.symtab import SymbolTable
from pyfront.types.types_builder import build_types


def run_generate(front_file: Path, output_dir: Path) -> None:
    """Read a .front file and write generation output into the output directory."""
    if front_file.suffix.lower() != ".front":
        raise ValueError("Input file must use the .front extension.")

    source = front_file.read_text(encoding="utf-8")

    parser = Parser(Lexer(Tokenizer(), source, eof_token=TokenType._EOF))
    front = parse_front(parser)
    SymbolTable.populate(front)
    model = build_types(front)

    generate_str_method(model)

    emitter = FolderEmitter(output_dir)
    with (
        emitter.mounted(report),
        emitter.open("model.py") as model_emitter,
        emitter.open("parser.py") as parser_emitter,
    ):
        GenerateModel(model, model_emitter).run()
        GenerateParser(front, parser_emitter).run()
