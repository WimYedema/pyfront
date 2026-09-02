from pathlib import Path


class GeneratorBase:
    def __init__(self) -> None:
        self.output = ""

    def print(self, text: str = "") -> None:
        self.output += text + "\n"

    def emit(self, path: Path) -> None:
        path.write_text(self.output, encoding="utf-8")
