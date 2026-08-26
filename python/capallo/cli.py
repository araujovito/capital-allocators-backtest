"""Ponto de entrada do pipeline.

Uso: capallo <comando>
"""

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="capallo")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("universe", help="lista o universo congelado de ativos")

    args = parser.parse_args(argv)

    if args.command == "universe":
        from capallo.universe import CAPITAL_ALLOCATORS, PASSIVE_ETFS

        for label, group in (("Capital Allocators", CAPITAL_ALLOCATORS), ("ETFs", PASSIVE_ETFS)):
            print(f"\n{label}")
            for a in group:
                print(f"  {a.region.value}  {a.ticker:<8} {a.name:<28} {a.exposure_currency.value}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
