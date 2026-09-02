import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pyfront.cmd.generate import run_generate


class RunGenerateTests(unittest.TestCase):
    def test_run_generate_writes_expected_output_file(self) -> None:
        source_content = "component App\nend\n"

        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            front_file = tmp_path / "input.front"
            output_dir = tmp_path / "nested" / "out"

            front_file.write_text(source_content, encoding="utf-8")

            result_path = run_generate(front_file, output_dir)

            self.assertEqual(output_dir / "generation.txt", result_path)
            self.assertTrue(result_path.exists())
            self.assertEqual(
                "\n".join(
                    [
                        "source_file=input.front",
                        f"source_chars={len(source_content)}",
                        "status=ok",
                        "",
                    ]
                ),
                result_path.read_text(encoding="utf-8"),
            )

    def test_run_generate_rejects_non_front_extension(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            front_file = tmp_path / "input.txt"
            output_dir = tmp_path / "out"

            front_file.write_text("content", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Input file must use the .front extension."):
                run_generate(front_file, output_dir)

    def test_run_generate_accepts_uppercase_front_extension(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            front_file = tmp_path / "input.FRONT"
            output_dir = tmp_path / "out"

            front_file.write_text("abc", encoding="utf-8")

            result_path = run_generate(front_file, output_dir)

            self.assertTrue(result_path.exists())


if __name__ == "__main__":
    unittest.main()
