import atexit
from textwrap import indent

from .emitter import Emitter, FolderEmitter


class _ReportEmitter(Emitter):
    nt_report: dict[str, dict[str, str]]

    def __init__(self):
        self.nt_report = {}
        self.indent = 0
        self.indentation = 4
        self._file = None
        self.path = None

    def nt_info(self, nt_name: str, info: str, text: str) -> None:
        """Store information about a non-terminal in the report."""
        if nt_name not in self.nt_report:
            self.nt_report[nt_name] = {}
        self.nt_report[nt_name][info] = text

    @property
    def is_enabled(self) -> bool:
        """Check if the report emitter is enabled."""
        return self._file is not None

    def open(self, parent: FolderEmitter) -> None:
        """Start the report emitter by opening the report file."""
        self.path = parent.output_dir / "report.md"
        self._file = open(self.path, "w", encoding="utf-8")

    def emit(self, text: str) -> None:
        """Emit the given text to the report file."""
        if self._file is not None:
            self._file.write(indent(text, " " * self.indent) + "\n")

    def emit_nt_info(self) -> None:
        """Emit the stored information for a specific non-terminal."""
        self.emit("\n# Non-Terminal Information")
        for nt_name in self.nt_report.keys():
            self.emit(f"\n## {nt_name}\n")
            for info, text in self.nt_report[nt_name].items():
                self.emit(f"* {info}: {text}")
        self.nt_report = {}  # Clear the report after emitting

    def close(self) -> None:
        """Close the report emitter by closing the report file."""
        if self._file:
            self.emit_nt_info()
            self._file.close()
            self._file = None


report: _ReportEmitter = _ReportEmitter()


def start_report(folder: FolderEmitter) -> None:
    """Start the report emitter.

    This function initializes the global report emitter and registers a cleanup
    function to close it at program exit.

    Args:
        folder (FolderEmitter): The folder emitter where the report file will be created.
    """
    global report
    report.open(folder)
    atexit.register(stop_report)  # Ensure the report is closed at program exit


def stop_report() -> None:
    """Stop the report emitter and close the report file."""
    global report
    report.close()
