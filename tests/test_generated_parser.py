import importlib
import sys
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from pyfront.cmd.generate import run_generate
from pyfront.support.ll_parser import LlSyntaxError


class GeneratedParserTests(unittest.TestCase):
    @contextmanager
    def generated_parser(self) -> Iterator[object]:
        grammar_file = Path(__file__).parents[1] / "sample.front"

        with TemporaryDirectory() as tmp_dir:
            package_dir = Path(tmp_dir) / "generated_front"
            package_dir.mkdir()
            (package_dir / "__init__.py").write_text("", encoding="utf-8")
            run_generate(grammar_file, package_dir)

            sys.path.insert(0, tmp_dir)
            try:
                yield importlib.import_module("generated_front.parser")
            finally:
                sys.path.remove(tmp_dir)
                sys.modules.pop("generated_front.parser", None)
                sys.modules.pop("generated_front.model", None)
                sys.modules.pop("generated_front", None)

    def test_generated_parser_parses_sample_input(self) -> None:
        with self.generated_parser() as parser:
            result = parser.parse('START A "foo" B 42')

        self.assertEqual("Root", result.__class__.__name__)
        self.assertEqual(
            [
                ("ElementA", '"foo"'),
                ("ElementB", "42"),
            ],
            [(element.__class__.__name__, element.value) for element in result.sequence],
        )

    def test_generated_parser_rejects_invalid_input(self) -> None:
        with self.generated_parser() as parser:
            with self.assertRaises(LlSyntaxError):
                parser.parse("START C value")

    def test_generated_parser_accepts_empty_repetition(self) -> None:
        with self.generated_parser() as parser:
            result = parser.parse("START")

        self.assertEqual([], result.sequence)

    def test_generated_parser_accepts_multiple_alternatives(self) -> None:
        with self.generated_parser() as parser:
            result = parser.parse('START B 1 A "two" B 3')

        self.assertEqual(
            [
                ("ElementB", "1"),
                ("ElementA", '"two"'),
                ("ElementB", "3"),
            ],
            [(element.__class__.__name__, element.value) for element in result.sequence],
        )

    def test_generated_parser_skips_whitespace_and_comments(self) -> None:
        with self.generated_parser() as parser:
            result = parser.parse('START // first element\n A "foo" // second element\n B 2')

        self.assertEqual(
            ["ElementA", "ElementB"],
            [element.__class__.__name__ for element in result.sequence],
        )

    def test_generated_parser_rejects_unexpected_eof(self) -> None:
        with self.generated_parser() as parser:
            with self.assertRaises(LlSyntaxError):
                parser.parse("START A")


if __name__ == "__main__":
    unittest.main()
