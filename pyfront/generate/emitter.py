from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path
from textwrap import indent


class Emitter:
    parent: Emitter | None
    indent: int = 0
    indentation: int = 4

    def __init__(self, parent: Emitter | None, indent: int = 0):
        self.parent = parent
        self.indent = indent
        self.indentation = parent.indentation if parent else 4

    def emit(self, text: str) -> None:
        """Emit the given text to the output."""
        if self.parent is None:
            raise ValueError("Cannot emit without a parent emitter")
        self.parent.emit(indent(text, " " * self.indent))

    def open_file(self, filename: str, indentation: int = 4) -> FileEmitter:
        """Create a FileEmitter for the given filename."""
        if self.parent is None:
            raise ValueError("Cannot open file without a parent emitter")
        return self.parent.open_file(filename, indentation)

    def block(self, prefix: str = "") -> Emitter:
        """Create a BlockEmitter for emitting indented blocks of text."""
        self.emit(prefix)
        return Emitter(self, indent=self.indent + self.indentation)

    def close(self) -> None:
        pass  # No action needed for base emitter

    @contextmanager
    def open(self, filename: str, indentation: int = 4) -> Iterable[FileEmitter]:
        """Context manager for opening a file emitter."""
        file_emitter = self.open_file(filename, indentation)
        try:
            yield file_emitter
        finally:
            file_emitter.close()


class FolderEmitter(Emitter):
    def __init__(self, output_dir: Path):
        super().__init__(parent=None, indent=0)
        self.output_dir = output_dir

    def open_file(self, filename: str, indentation: int = 4) -> FileEmitter:
        """Create a FileEmitter for the given filename."""
        return FileEmitter(self, filename, indentation)


class FileEmitter(Emitter):
    def __init__(self, parent: FolderEmitter, filename: str, indentation: int = 4):
        super().__init__(parent=parent, indent=0)
        self.path = parent.output_dir / filename
        self.indentation = indentation
        self._file = open(self.path, "w", encoding="utf-8")

    def emit(self, text: str) -> None:
        """Write the given text to the file."""
        self._file.write(indent(text, " " * self.indent) + "\n")

    def close(self) -> None:
        """Close the file emitter."""
        self._file.close()
