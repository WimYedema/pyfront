from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")

_position_map: dict[int, Position] = {}


def _add_position(obj: object, position: Position) -> None:
    _position_map[id(obj)] = position


def _get_position(obj: object) -> Position | None:
    return _position_map.get(id(obj))


@dataclass(frozen=True)
class Position:
    charno: int
    line: int
    column: int
    path: str = "<input>"

    @classmethod
    def none(cls) -> Position:
        return cls(charno=0, line=0, column=0, path="<missing>")

    @classmethod
    def start_of_file(cls, path: str = "<input>") -> Position:
        return cls(charno=0, line=1, column=1, path=path)

    def advance(self, text: str) -> Position:
        num_newlines = text.count("\n")
        new_col = self.column if num_newlines == 0 else 1
        new_col += len(text.split("\n")[-1])
        return Position(
            charno=self.charno + len(text),
            line=self.line + num_newlines,
            column=new_col,
            path=self.path,
        )

    def display(self) -> str:
        return f"{self.path}:{self.line}:{self.column}"

    def record(self, obj: T) -> T:
        _add_position(obj, self)
        return obj

    @classmethod
    def from_object(cls, obj: object) -> Position | None:
        return _get_position(obj)
