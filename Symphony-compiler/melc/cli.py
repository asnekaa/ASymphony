from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .compiler import CompileError, compile_source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile Melody source to Symphony assembly.")
    parser.add_argument("input", type=Path, help="input .mel file")
    parser.add_argument("-o", "--output", type=Path, help="output assembly .txt file")
    args = parser.parse_args(argv)

    try:
        source = args.input.read_text(encoding="utf-8")
        assembly = compile_source(source)
    except OSError as exc:
        print(f"melc: {exc}", file=sys.stderr)
        return 1
    except CompileError as exc:
        print(f"melc: {exc}", file=sys.stderr)
        return 2

    if args.output:
        args.output.write_text(assembly, encoding="utf-8")
    else:
        print(assembly, end="")

    return 0
