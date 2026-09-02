import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pyfront.generate.emitter import FolderEmitter


class EmitterTests(unittest.TestCase):
    def test_open_emits_nested_blocks_and_closes_file(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "generated.py"
            with FolderEmitter(Path(tmp_dir)).open("generated.py") as emitter:
                emitter.block("if enabled:").emit("emit_value()")

            self.assertEqual("if enabled:\n    emit_value()\n", output_path.read_text())


if __name__ == "__main__":
    unittest.main()
