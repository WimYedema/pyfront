from pathlib import Path

from pyfront.generate.model import GenerateModel
from pyfront.generate.parser import GenerateParser
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

    model_generator = GenerateModel(front).run()
    parser_generator = GenerateParser(front).run()

    output_dir.mkdir(parents=True, exist_ok=True)

    model_generator.emit(output_dir / "model.py")
    parser_generator.emit(output_dir / "parser.py")
