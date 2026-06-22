from __future__ import annotations

import argparse
import sys

from . import ema, fda


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect health-authority guidance documents.")
    subparsers = parser.add_subparsers(dest="authority", required=True)
    subparsers.add_parser("fda", help="Collect FDA guidance. Use python -m guidance_collector.fda for all options.")
    subparsers.add_parser("ema", help="Collect EMA guidance. Use python -m guidance_collector.ema for all options.")
    args, remaining = parser.parse_known_args(argv)
    if args.authority == "fda":
        return fda.main(remaining)
    if args.authority == "ema":
        return ema.main(remaining)
    return 2


if __name__ == "__main__":
    sys.exit(main())
