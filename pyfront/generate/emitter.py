from __future__ import annotations

from collections.abc import Generator, Iterable
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent, indent
from typing import Self, TextIO, TypeVar


class Emitter:
    parent: Emitter | None
    _indent: int = 0
    indentation: int = 4

    def __init__(self, parent: Emitter | None, indent: int = 0):
        self.parent = parent
        self._indent = indent
        self.indentation = parent.indentation if parent else 4

    def preformat(self, text: str) -> str:
        if text[0:2] == "\n ":
            return dedent(text[1:])
        else:
            return dedent(text)

    def emit(self, text: str = "") -> Self:
        """Emit the given text to the output."""
        if self.parent is None:
            raise ValueError("Cannot emit without a parent emitter")
        self.parent.emit(indent(self.preformat(text), " " * self._indent))
        return self

    def mount(self, emitter: Emitter) -> None:
        if self.parent is None:
            raise ValueError("Cannot mount an emitter without a parent emitter")
        return self.parent.mount(emitter)

    @contextmanager
    def mounted(self, emitter: E) -> Generator[E]:
        """Context manager for mounting an emitter."""
        try:
            yield self.mount(emitter)
        finally:
            emitter.close()

    def open_file(self, filename: str, indentation: int = 4) -> FileEmitter:
        """Create a FileEmitter for the given filename."""
        if self.parent is None:
            raise ValueError("Cannot open file without a parent emitter")
        return self.parent.open_file(filename, indentation)

    def block(self, prefix: str = "") -> Emitter:
        """Create an Emitter for emitting indented blocks of text."""
        self.emit(prefix)
        return Emitter(self, indent=self._indent + self.indentation)

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

    def indent(self) -> Self:
        self._indent += self.indentation
        return self

    def dedent(self) -> Self:
        self._indent -= self.indentation
        return self


E = TypeVar("E", bound=Emitter)


class FolderEmitter(Emitter):
    def __init__(self, output_dir: Path):
        super().__init__(parent=None, indent=0)
        self.output_dir = output_dir

    def open_file(self, filename: str, indentation: int = 4) -> FileEmitter:
        """Create a FileEmitter for the given filename."""
        return self.mount(FileEmitter(filename, indentation))

    def mount(self, emitter: E) -> E:
        emitter.on_mount(self.output_dir)
        return emitter


class FileEmitter(Emitter):
    def __init__(self, filename: str, indentation: int = 4):
        super().__init__(parent=None, indent=0)
        self.filename = filename
        self.indentation = indentation
        self._file: TextIO | None = None

    def on_mount(self, output_dir: Path) -> None:
        self._file = open(output_dir / self.filename, "w", encoding="utf-8")

    def emit(self, text: str = "") -> Self:
        """Write the given text to the file."""
        if self._file is not None:
            self._file.write(indent(text, " " * self._indent) + "\n")
        return self

    def close(self) -> None:
        """Close the file emitter."""
        if self._file is not None:
            self._file.close()
            self._file = None


class StringEmitter(Emitter):
    def __init__(self, indentation: int = 4):
        super().__init__(parent=None, indent=0)
        self.indentation = indentation
        self._content: str = ""

    def emit(self, text: str = "") -> Self:
        """Write the given text to the file."""
        self._content += indent(text, " " * self._indent) + "\n"
        return self

    def get_content(self) -> str:
        return self._content

    def open_file(self, filename: str, indentation: int = 4) -> Emitter:
        """Opening files is not supported for StringEmitter."""
        raise NotImplementedError("StringEmitter does not support opening files")
