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
    p_un = sub.add_parser("build-us-net", help="aplica a retencao na fonte a serie americana")
    p_un.add_argument("--curated", default="data/curated")
    p_ti = sub.add_parser("build-intl", help="monta o total return de Europa e Japao")
    p_ti.add_argument("--out", default="data/curated")
    p_ds = sub.add_parser("export-dataset", help="prepara o dataset para o motor Rust")
    p_ds.add_argument("--curated", default="data/curated")
    p_ds.add_argument("--out", default="data/engine")
    p_intl = sub.add_parser("fetch-intl", help="precos de Japao (Kabutan) e Suecia (Avanza)")
    p_intl.add_argument("--out", default="data/curated")
    p_jc = sub.add_parser("check-jp-prices",
                          help="confere a serie do Kabutan contra o preco publicado pelas companhias")
    p_jc.add_argument("--curated", default="data/curated")
    p_jc.add_argument("--manual", default="data/manual")
    p_jp = sub.add_parser("fetch-jp-dividends", help="proventos de 8058 e 8031, dos relatorios anuais")
    p_jp.add_argument("--out", default="data/curated")
    p_jp.add_argument("--raw", default="data/raw/reports")
    p_se = sub.add_parser("fetch-se-dividends", help="proventos de INVE-B, pelo IR da Investor AB")
    p_se.add_argument("--out", default="data/curated")
    p_dc = sub.add_parser("decompose", help="retorno de cada ativo entre ativo, cambio e inflacao")
    p_dc.add_argument("--curated", default="data/curated")
    p_dc.add_argument("--engine", default="data/engine")
    p_dc.add_argument("--results", default="data/results")
    p_pr = sub.add_parser("premium", help="Allocator Premium por regiao, ao lado do risco")
    p_pr.add_argument("--results", default="data/results")
    p_pr.add_argument("--curated", default="data/curated")
    p_cr = sub.add_parser("crises", help="comportamento das estrategias em recortes de crise")
    p_cr.add_argument("--results", default="data/results")
    p_cr.add_argument("--curated", default="data/curated")
    p_cr.add_argument("--strategies", default="strategies")
    p_sn = sub.add_parser("sensitivity",
                          help="quanto as escolhas de metodo decidem o resultado")
    p_sn.add_argument("experimento", choices=["ptax", "janelas", "all"], nargs="?", default="all")
    p_sn.add_argument("--curated", default="data/curated")
    p_sn.add_argument("--engine-dir", default="engine")
    p_sn.add_argument("--engine-data", default="data/engine")
    p_sn.add_argument("--strategies", default="strategies")
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

    if args.command == "build-us-net":
        from pathlib import Path

        from capallo.transform.us_net import build, custo_da_retencao, validate

        curated = Path(args.curated)
        build(curated)
        print(f"  {'ativo':<8}{'aliquota':>9}{'yield bruto':>13}{'bruto':>9}{'liquido':>9}{'custo a.a.':>12}")
        for _, r in custo_da_retencao(curated).iterrows():
            print(f"  {r.ticker:<8}{r.aliquota:>8.0%}{r.yield_bruto_aa:>13.2%}"
                  f"{r.bruto:>8.2f}x{r.liquido:>8.2f}x{r.custo_pp_aa:>11.2f}p")
        problems = validate(curated)
        if problems:
            print("\nPROBLEMAS:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print("\n  BRK-B e MKL nao pagam dividendo: custo zero confirma o metodo")
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

    if args.command == "check-jp-prices":
        from capallo.ingest.kabutan import conferir_contra_relatorio, veredito_da_serie

        conf = conferir_contra_relatorio(args.curated, args.manual)
        print(f"  {'ativo':<7}{'exerc.':>7}{'tipo':>16}{'publicado':>11}"
              f"{'coletado':>10}{'razao':>8}   fonte")
        for _, r in conf.iterrows():
            print(f"  {r.ticker:<7}{r.exercicio:>7}{r.tipo:>16}{r.publicado:>11,.1f}"
                  f"{r.coletado:>10,.1f}{r.razao:>8.3f}   {r.fonte}")
        print("\n  razao media por ativo:")
        for ticker, g in conf.groupby("ticker"):
            print(f"    {ticker}  {g.razao.mean():.4f}  ({len(g)} pontos)")
        print("\n  uma serie ajustada por dividendo apareceria perto de 0,50 nesta"
              " ponta da janela")

        problems = veredito_da_serie(conf)
        if problems:
            print("\nPROBLEMAS:")
            for pb in problems:
                print(f"  - {pb}")
            return 1
        print("\nvalidacao ok — serie e preco puro; o provento japones entra por fora")
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

    if args.command == "fetch-se-dividends":
        from pathlib import Path

        from capallo.ingest.investor_ir import build, conferir_avanza, evidencia_data_ex, validate

        out = Path(args.out)
        df = build(out)
        print(f"  INVE-B  {len(df):>3} proventos entre {df.ex_date.min().date()} "
              f"e {df.ex_date.max().date()}")

        # A pergunta que este coletor existe para responder: a serie de preco da
        # Avanza ja embute o dividendo? Se embutisse, o papel nao cairia na data-ex.
        ev = evidencia_data_ex(out)
        print(f"\ncomportamento do preco na data-ex, em {len(ev)} eventos:")
        print(f"  retorno medio no dia-ex   {ev.retorno_pct.mean():+7.3f}%")
        print(f"  dividendo esperado        {ev.dividendo_pct.mean():+7.3f}%")
        print(f"  residuo                   {ev.attrs['residuo_pp']:+7.3f} p.p.")
        print(f"  um dia qualquer           {ev.attrs['dia_qualquer_pct']:+7.3f}%"
              f"  (dp {ev.attrs['dp_diario_pct']:.2f}%)")
        print(f"  t contra zero             {ev.attrs['t_stat']:>7.2f}")
        veredito = ("preco puro — o provento PRECISA ser somado"
                    if ev.attrs["t_stat"] < -2 else "total return — nao somar provento")
        print(f"  veredito: {veredito}")

        divergencias = conferir_avanza(out)
        print("\nconferencia contra a Avanza, onde as duas fontes se sobrepoem:")
        for d in divergencias or ["  sem divergencia"]:
            print(f"  {d}" if divergencias else d)

        problems = validate(out)
        if problems:
            print("\nPROBLEMAS:")
            for pb in problems:
                print(f"  - {pb}")
            return 1
        print("\nvalidacao ok")
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

    if args.command == "crises":
        from pathlib import Path

        from capallo.analysis.crises import (
            CRISES,
            confronto,
            placar_de_protecao,
            tabela,
            validate,
        )

        results, curated = Path(args.results), Path(args.curated)
        strategies = Path(args.strategies)

        print("  janelas datadas por terceiros, antes de olhar o resultado:")
        for cr in CRISES:
            print(f"    {cr.nome:<26}{cr.inicio} a {cr.fim}   {cr.fonte}")

        t = tabela(results, curated, ("capital_allocators", "passive_etfs", "cdi"))
        print(f"\n  retorno real dentro da janela, aporte expurgado:\n"
              f"    {'crise':<26}{'estrategia':<20}{'retorno':>9}{'queda':>9}{'recup.':>8}")
        for _, r in t.iterrows():
            rec = "—" if r.recuperacao_meses is None else f"{r.recuperacao_meses}m"
            print(f"    {r.crise:<26}{r.estrategia:<20}{r.retorno:>8.1%}"
                  f"{r.queda_max:>9.1%}{rec:>8}")

        print("\n  allocator contra o ETF da mesma regiao, crise a crise:")
        for _, r in placar_de_protecao(results, curated).iterrows():
            print(f"    {r.regiao:<8}{r.venceu}/{r.crises} crises   "
                  f"media {r.media_pp:+.1f} p.p.")

        piores = confronto(results, curated).nsmallest(3, "diferenca_pp")
        print("\n  onde a gestao ativa mais atrapalhou:")
        for _, r in piores.iterrows():
            print(f"    {r.crise:<26}{r.regiao:<8}{r.diferenca_pp:+7.1f} p.p.")

        problems = validate(results, curated, strategies)
        if problems:
            print("\nPROBLEMAS:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print("\n  regras congeladas: todas as estrategias compartilham janela, "
              "aporte e regra de dividendo")
        return 0

    if args.command == "sensitivity":
        from pathlib import Path

        from capallo.analysis.sensitivity import janelas_de_inicio, ponta_da_ptax

        curated, eng = Path(args.curated), Path(args.engine_dir)
        strat, edata = Path(args.strategies), Path(args.engine_data)
        ordem = ["Brasil", "EUA", "Europa", "Japão", "Global"]

        if args.experimento in ("ptax", "all"):
            print("PONTA DA PTAX — premio em p.p. a.a. por ponta de conversao\n")
            df = ponta_da_ptax(curated, eng, strat)
            piv = df.pivot(index="regiao", columns="ponta", values="premio_pp").reindex(ordem)
            print(f"  {'regiao':<8}{'venda':>9}{'compra':>9}{'media':>9}{'venda-compra':>14}")
            for regiao, r in piv.iterrows():
                print(f"  {regiao:<8}{r['ask']:>9.3f}{r['bid']:>9.3f}{r['mid']:>9.3f}"
                      f"{r['ask'] - r['bid']:>14.3f}")
            print("\n  o residuo aparece so onde as duas pernas usam moedas diferentes:")
            print("  Brasil nao tem cambio; nos EUA as duas pernas sao USD e o spread cancela")
            print("  exatamente; na Europa e no Japao o ETF liquida em USD e o allocator nao.")
            maior = piv.apply(lambda r: abs(r["ask"] - r["bid"]), axis=1).max()
            print(f"  maior efeito: {maior:.3f} p.p. a.a. — a escolha nao decide"
                  " veredito nenhum.")

        if args.experimento in ("janelas", "all"):
            print("\n\nJANELAS DE INICIO — premio em p.p. a.a., sempre ate dez/2025\n")
            df = janelas_de_inicio(curated, eng, strat, edata)
            piv = df.pivot(index="inicio", columns="regiao", values="premio_pp")[ordem]
            print("  inicio " + "".join(f"{c:>9}" for c in ordem))
            for ano, r in piv.iterrows():
                print(f"  {ano:<7}" + "".join(f"{v:>9.2f}" for v in r))
            n = len(piv)
            print(f"\n  janelas com premio positivo, de {n}:")
            for regiao in ordem:
                pos = int((piv[regiao] > 0).sum())
                marca = "  <-- o placar de 2006 e a unica janela positiva" if pos == 1 else ""
                print(f"    {regiao:<8}{pos:>3}/{n}{marca}")

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
