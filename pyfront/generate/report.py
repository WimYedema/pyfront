from .emitter import FileEmitter


class _ReportEmitter(FileEmitter):
    nt_report: dict[str, dict[str, str]]

    def __init__(self):
        super().__init__("report.md")
        self.nt_report = {}

    def nt_info(self, nt_name: str, info: str, text: str) -> None:
        """Store information about a non-terminal in the report."""
        if nt_name not in self.nt_report:
            self.nt_report[nt_name] = {}
        self.nt_report[nt_name][info] = text

    @property
    def is_enabled(self) -> bool:
        """Check if the report emitter is enabled."""
        return self._file is not None

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
