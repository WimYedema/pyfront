from pathlib import Path


def run_generate(front_file: Path, output_dir: Path) -> Path:
    """Read a .front file and write generation output into the output directory."""
    if front_file.suffix.lower() != ".front":
        raise ValueError("Input file must use the .front extension.")

    source = front_file.read_text(encoding="utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "generation.txt"
    output_file.write_text(
        "\n".join(
            [
                f"source_file={front_file.name}",
                f"source_chars={len(source)}",
                "status=ok",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return output_file
