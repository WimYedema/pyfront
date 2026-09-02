from textwrap import dedent
from typing import Self

from pyfront.generate.emitter import Emitter


class GeneratorBase:
    def __init__(self, emitter: Emitter) -> None:
        self.emitter = emitter

    def emit(self, text: str = "") -> Self:
        if text[0:2] == "\n ":
            self.emitter.emit(dedent(text[1:]))
        else:
            self.emitter.emit(dedent(text))
        return self

    def indent(self) -> Self:
        self.emitter.indent += self.emitter.indentation
        return self

    def dedent(self) -> Self:
        self.emitter.indent -= self.emitter.indentation
        return self
