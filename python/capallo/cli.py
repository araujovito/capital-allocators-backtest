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
    p_tr = sub.add_parser("build-br", help="monta o total return brasileiro")
    p_tr.add_argument("--out", default="data/curated")
    p_ti = sub.add_parser("build-intl", help="monta o total return de Europa e Japao")
    p_ti.add_argument("--out", default="data/curated")
    p_ds = sub.add_parser("export-dataset", help="prepara o dataset para o motor Rust")
    p_ds.add_argument("--curated", default="data/curated")
    p_ds.add_argument("--out", default="data/engine")
    p_intl = sub.add_parser("fetch-intl", help="precos de Japao (Kabutan) e Suecia (Avanza)")
    p_intl.add_argument("--out", default="data/curated")
    p_jp = sub.add_parser("fetch-jp-dividends", help="proventos de 8058 e 8031, dos relatorios anuais")
    p_jp.add_argument("--out", default="data/curated")
    p_jp.add_argument("--raw", default="data/raw/reports")
    p_dc = sub.add_parser("decompose", help="retorno de cada ativo entre ativo, cambio e inflacao")
    p_dc.add_argument("--curated", default="data/curated")
    p_dc.add_argument("--engine", default="data/engine")
    p_dc.add_argument("--results", default="data/results")
    p_pr = sub.add_parser("premium", help="Allocator Premium por regiao, ao lado do risco")
    p_pr.add_argument("--results", default="data/results")
    p_pr.add_argument("--curated", default="data/curated")
    p_sb = sub.add_parser("scoreboard", help="placar comparativo entre estrategias")
    p_sb.add_argument("--results", default="data/results")
    p_sb.add_argument("--curated", default="data/curated")

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

    if args.command == "build-br":
        from pathlib import Path

        from capallo.transform.build_br import build, validate

        out = Path(args.out)
        df = build(out)
        for t, g in df.groupby("ticker"):
            g = g.sort_values("date")
            tr = g.tr_index.iloc[-1] / g.tr_index.iloc[0]
            print(f"  {t:<8}{g.units.iloc[-1]:>9.3f} unidades   "
                  f"{(tr - 1) * 100:>8.1f}%   {(tr ** (1 / 20) - 1) * 100:>5.2f}% a.a.")
        problems = validate(out)
        if problems:
            print("\nPROBLEMAS:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print("\nvalidacao ok — nenhum salto residual")
        return 0

    if args.command == "build-intl":
        from pathlib import Path

        from capallo.transform.build_intl import build, sensibilidade, validate

        out = Path(args.out)
        df = build(out)
        for t, g in df.groupby("ticker"):
            g = g.sort_values("date")
            tr = g.tr_index.iloc[-1] / g.tr_index.iloc[0]
            print(f"  {t:<8}{g.units.iloc[-1]:>7.3f} unidades   "
                  f"{(tr - 1) * 100:>8.1f}%   {(tr ** (1 / 20) - 1) * 100:>5.2f}% a.a. em moeda local")
        print("\ncusto da convencao de data-ex japonesa, em 20 anos:")
        for _, r in sensibilidade(out).iterrows():
            print(f"  {r.ticker}  duas parcelas {r.duas_parcelas:.2f}x  "
                  f"parcela unica {r.parcela_unica:.2f}x  diferenca {r.diferenca_pp:+.2f}%")
        problems = validate(out)
        if problems:
            print("\nPROBLEMAS:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print("\nvalidacao ok")
        return 0

    if args.command == "export-dataset":
        from pathlib import Path

        from capallo.transform.dataset import export

        for k, v in export(Path(args.curated), Path(args.out)).items():
            print(f"  {k:<10}{v:>7}")
        return 0

    if args.command == "fetch-intl":
        from pathlib import Path

        from capallo.ingest.international import build, validate

        out = Path(args.out)
        for name, n in build(out).items():
            print(f"  {name:<8}{n:>5} meses")
        problems = validate(out)
        if problems:
            print("\nPROBLEMAS:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print("\nvalidacao ok  (ATENCAO: preco, ainda sem proventos)")
        return 0

    if args.command == "fetch-jp-dividends":
        from pathlib import Path

        from capallo.ingest.jp_reports import build, conferir_irbank, validate

        out = Path(args.out)
        df = build(out, Path(args.raw))
        for ticker, g in df.groupby("ticker"):
            cruzados = int((g.fontes > 1).sum())
            print(f"  {ticker}  {len(g):>3} exercicios   {cruzados:>2} conferidos em duas fontes")
        divergencias = conferir_irbank(out)
        print("\nconferencia independente contra o IR Bank (2010-2013):")
        for d in divergencias or ["  sem divergencia"]:
            print(f"  {d}" if divergencias else d)
        problems = validate(out)
        if problems:
            print("\nPROBLEMAS:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print("\nvalidacao ok — 2006-2025 completo, em acoes pos-desdobramento")
        return 0

    if args.command == "decompose":
        from pathlib import Path

        from capallo.analysis.decomposition import by_asset, validate

        curated, engine = Path(args.curated), Path(args.engine)
        df = by_asset(curated, engine)
        print(f"  {'ativo':<8}{'moeda':<7}{'ativo':>9}{'cambio':>9}{'nominal':>10}"
              f"{'real':>9}   {'ativo a.a.':>10}{'cambio a.a.':>12}{'real a.a.':>10}")
        for _, r in df.iterrows():
            wrapper = "*" if r.moeda_exposicao != r.moeda_negociacao else " "
            print(f"  {r.ticker:<8}{r.moeda_exposicao}{wrapper:<5} {r.local:>8.2f}x{r.cambio:>8.2f}x"
                  f"{r.nominal_brl:>9.2f}x{r.real_brl:>8.2f}x   {r.local_aa:>9.2%}"
                  f"{r.cambio_aa:>11.2%}{r.real_brl_aa:>10.2%}")
        print("\n  * wrapper em dolar: o cambio e atribuido a moeda do mercado subjacente")
        problems = validate(Path(args.results), curated, engine)
        if problems:
            print("\nPROBLEMAS:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print("  identidade ativo x cambio = retorno em BRL fecha em todos os ativos")
        return 0

    if args.command == "premium":
        from pathlib import Path

        from capallo.analysis.decomposition import (
            contribuicao_por_ativo,
            premium,
            resumo_global,
            sem_o_melhor,
        )

        results, curated = Path(args.results), Path(args.curated)
        print(f"  {'regiao':<8}{'alloc':>8}{'etf':>8}{'premio':>9}{'vol extra':>11}"
              f"{'d sharpe':>10}{'d maxDD':>9}   veredito")
        for _, r in premium(results, curated).iterrows():
            print(f"  {r.regiao:<8}{r.alloc_real_aa:>7.2%}{r.etf_real_aa:>8.2%}"
                  f"{r.premio_pp:>8.2f}p{r.vol_extra_pp:>10.2f}p{r.delta_sharpe:>10.2f}"
                  f"{r.delta_max_dd_pp:>8.1f}p   {r.veredito}")

        g = resumo_global(results, curated)
        print(f"\n  global: allocators {g['allocators_reais_por_real']:.2f}x contra "
              f"{g['etfs_reais_por_real']:.2f}x do passivo, "
              f"{g['premio_pp']:+.2f} p.p. ao ano")

        print("\n  concentracao da carteira ativa (peso final):")
        for _, r in contribuicao_por_ativo(results, "capital_allocators").iterrows():
            print(f"    {r.ticker:<8}{r.peso_final:>7.1%}")
        c = sem_o_melhor(results, curated, "capital_allocators")
        print(f"    maior peso {c['ativo_dominante']} com {c['peso_final']:.1%}; "
              f"HHI {c['concentracao_hhi']:.3f}")
        return 0

    if args.command == "scoreboard":
        from pathlib import Path

        import pandas as pd

        from capallo.analysis.scoreboard import build, win_rate

        names = {"br_allocators": "BR Alloc", "br_etf": "BR ETF",
                 "us_allocators": "US Alloc", "us_etf": "US ETF",
                 "eu_allocators": "EU Alloc", "eu_etf": "EU ETF",
                 "jp_allocators": "JP Alloc", "jp_etf": "JP ETF", "cdi": "CDI"}
        results, curated = Path(args.results), Path(args.curated)
        df = build(results, curated, names)
        fmt = {"patrimonio_nominal": "{:,.0f}", "aportado_real": "{:,.0f}",
               "reais_por_real": "{:.2f}", "retorno_real_aa": "{:.2%}",
               "volatilidade": "{:.2%}", "max_drawdown": "{:.1%}",
               "recuperacao_meses": "{:.0f}", "sharpe": "{:.2f}",
               "sortino": "{:.2f}", "melhor_12m": "{:.1%}", "pior_12m": "{:.1%}"}
        out = pd.DataFrame(index=df.index, columns=df.columns, dtype=object)
        for k in df.index:
            for c in df.columns:
                v = df.loc[k, c]
                out.loc[k, c] = "—" if pd.isna(v) else fmt.get(k, "{}").format(v)
        print(out.to_string())

        print("\nvitorias dos allocators sobre o ETF, em janelas moveis:")
        for region, a, b in (("Brasil", "br_allocators", "br_etf"),
                             ("EUA", "us_allocators", "us_etf"),
                             ("Europa", "eu_allocators", "eu_etf"),
                             ("Japao", "jp_allocators", "jp_etf")):
            for years in (1, 3, 5, 10):
                w = win_rate(results / f"{a}.csv", results / f"{b}.csv", years)
                print(f"   {region:<7}{years:>3} anos: {w:.0%}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
