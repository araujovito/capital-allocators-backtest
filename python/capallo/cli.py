"""Ponto de entrada do pipeline.

Uso: capallo <comando>
"""

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="capallo")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("universe", help="lista o universo congelado de ativos")
    p_probe = sub.add_parser("probe", help="spike de viabilidade dos dados")
    p_probe.add_argument("tickers", nargs="*", help="subconjunto a testar (default: todos)")
    p_probe.add_argument("--pause", type=float, default=1.5)
    p_macro = sub.add_parser("fetch-macro", help="baixa e valida CDI, IPCA e PTAX")
    p_macro.add_argument("--out", default="data/curated")
    p_eq = sub.add_parser("fetch-equities", help="baixa as series de renda variavel disponiveis")
    p_eq.add_argument("--out", default="data/curated")
    p_b3 = sub.add_parser("fetch-b3", help="baixa e valida os precos da B3 (COTAHIST)")
    p_b3.add_argument("--out", default="data/curated")
    p_b3.add_argument("--raw", default="data/raw")
    p_ev = sub.add_parser("fetch-b3-events", help="proventos e eventos societarios da B3")
    p_ev.add_argument("--out", default="data/curated")

    args = parser.parse_args(argv)

    if args.command == "universe":
        from capallo.universe import CAPITAL_ALLOCATORS, PASSIVE_ETFS

        for label, group in (("Capital Allocators", CAPITAL_ALLOCATORS), ("ETFs", PASSIVE_ETFS)):
            print(f"\n{label}")
            for a in group:
                print(f"  {a.region.value}  {a.ticker:<8} {a.name:<28} {a.exposure_currency.value}")
        return 0

    if args.command == "probe":
        from capallo.ingest.probe_report import render, run

        print(render(run(args.tickers or None, pause=args.pause)))
        return 0

    if args.command == "fetch-macro":
        from pathlib import Path

        from capallo.ingest.macro import build, validate

        out = Path(args.out)
        for name, n in build(out).items():
            print(f"  {name:<8}{n:>6} obs")
        problems = validate(out)
        if problems:
            print("\nPROBLEMAS:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print("\nvalidacao ok")
        return 0

    if args.command == "fetch-equities":
        from pathlib import Path

        from capallo.ingest.equities import build, validate

        out = Path(args.out)
        for name, n in build(out).items():
            print(f"  {name:<8}{n:>6} meses")
        problems = validate(out)
        if problems:
            print("\nPROBLEMAS:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print("\nvalidacao ok")
        return 0

    if args.command == "fetch-b3":
        from pathlib import Path

        from capallo.ingest.b3 import build, validate

        out = Path(args.out)
        for name, n in build(out, Path(args.raw)).items():
            print(f"  {name:<8}{n:>6} pregoes")
        problems = validate(out)
        if problems:
            print("\nPROBLEMAS:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print("\nvalidacao ok  (ATENCAO: precos brutos, sem proventos)")
        return 0

    if args.command == "fetch-b3-events":
        from capallo.ingest.b3_events import build, reconcile

        for name, n in build(args.out).items():
            print(f"  {name:<20}{n:>5}")
        warnings = reconcile(args.out)
        if warnings:
            print("\nRECONCILIACAO — dados suspeitos:")
            for w in warnings:
                print(f"  ! {w}")
            return 0
        print("\nreconciliacao ok")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
