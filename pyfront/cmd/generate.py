from pathlib import Path

from pyfront.generate.emitter import FolderEmitter
from pyfront.generate.model import GenerateModel
from pyfront.generate.parser import GenerateParser
from pyfront.generate.report import start_report, stop_report
from pyfront.lang.grammar import Tokenizer, TokenType, parse_front
from pyfront.lang.parser import Parser
from pyfront.normalize import Normalize
from pyfront.support.lexer import Lexer
from pyfront.symtab import SymbolTable


def run_generate(front_file: Path, output_dir: Path) -> None:
    """Read a .front file and write generation output into the output directory."""
    if front_file.suffix.lower() != ".front":
        raise ValueError("Input file must use the .front extension.")

    source = front_file.read_text(encoding="utf-8")

    parser = Parser(Lexer(Tokenizer(), source, eof_token=TokenType._EOF))
    front = parse_front(parser)
    SymbolTable.populate(front)
    Normalize(front).run()

    emitter = FolderEmitter(output_dir)
    start_report(emitter)
    with emitter.open("model.py") as model_emitter, emitter.open("parser.py") as parser_emitter:
        GenerateModel(front, model_emitter).run()
        GenerateParser(front, parser_emitter).run()
    stop_report()
