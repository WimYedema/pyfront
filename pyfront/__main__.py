from pathlib import Path

import click

from pyfront.cmd.generate import run_generate


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--debug", is_flag=True, help="Enable debug mode.")
@click.version_option(package_name="pyfront", prog_name="pyfront")
def main(debug: bool) -> None:
    """Pyfront command line interface."""
    if debug:
        import logging

        logging.basicConfig(level=logging.DEBUG)


@main.command("generate")
@click.argument("front_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output_dir", type=click.Path(file_okay=False, path_type=Path))
def generate(front_file: Path, output_dir: Path) -> None:
    """Generate output files from a .front input file into OUTPUT_DIR."""
    try:
        run_generate(front_file, output_dir)
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="front_file") from exc
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc


if __name__ == "__main__":
    main()
