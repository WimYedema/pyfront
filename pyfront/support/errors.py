from pyfront.support.position import Position


class InputError(Exception):
    """Exception raised for errors in the input."""

    def __init__(self, position: Position | None, message: str):
        self.position = position or Position.none()
        super().__init__(f"{self.position.display()}: {message}")


class SyntaxError(InputError):
    """Exception for syntax errors in the lexer."""

    def __init__(self, position: Position, character: str):
        super().__init__(position, f"Unexpected character: {character}")
        self.character = character


class AstError(InputError):
    """Exception for source-level errors detected in the AST."""

    def __init__(self, node: object, message: str):
        super().__init__(Position.from_object(node), message)
