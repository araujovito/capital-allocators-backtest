//! Motor de backtest.
//!
//! O motor não conhece gráficos nem interface: recebe uma estratégia e um
//! dataset, calcula, e devolve os estados da carteira.

mod data;
mod engine;
mod strategy;

use anyhow::Context;
use clap::{Parser, Subcommand};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "backtest", version)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Carrega e valida um arquivo de estratégia sem executá-la.
    Validate { strategy: PathBuf },
    /// Executa o backtest.
    Run {
        strategy: PathBuf,
        #[arg(long, default_value = "../data/engine")]
        data: PathBuf,
        /// Arquivo CSV com a série mensal da carteira.
        #[arg(long)]
        out: Option<PathBuf>,
        /// Arquivo CSV com a posição por ativo, mês a mês. Sem isto não é
        /// possível calcular contribuição individual nem Allocator Premium.
        #[arg(long)]
        positions: Option<PathBuf>,
    },
}

fn load(path: &PathBuf) -> anyhow::Result<strategy::Strategy> {
    let text = std::fs::read_to_string(path)
        .with_context(|| format!("lendo estratégia em {}", path.display()))?;
    let parsed: strategy::StrategyFile = toml::from_str(&text)?;
    parsed.strategy.validate()?;
    Ok(parsed.strategy)
}

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Command::Validate { strategy } => {
            let s = load(&strategy)?;
            println!("ok: {} ({} ativos, {} → {})", s.name, s.weights.len(), s.start, s.end);
        }
        Command::Run { strategy, data, out, positions } => {
            let s = load(&strategy)?;
            let ds = data::Dataset::load(&data)?;
            let states = engine::run(&s, &ds)?;

            if let Some(path) = &out {
                let mut w = csv::Writer::from_path(path)?;
                w.write_record(["month", "contribution", "contributed_cum", "value"])?;
                for st in &states {
                    w.write_record([
                        &st.month,
                        &format!("{:.6}", st.contribution),
                        &format!("{:.6}", st.contributed_cum),
                        &format!("{:.6}", st.value),
                    ])?;
                }
                w.flush()?;
                println!("{} meses gravados em {}", states.len(), path.display());
            }

            if let Some(path) = &positions {
                let mut w = csv::Writer::from_path(path)?;
                w.write_record(["month", "ticker", "units", "price", "value", "invested"])?;
                for st in &states {
                    for p in &st.positions {
                        w.write_record([
                            &st.month,
                            &p.ticker,
                            &format!("{:.10}", p.units),
                            &format!("{:.6}", p.price),
                            &format!("{:.6}", p.value),
                            &format!("{:.6}", p.invested),
                        ])?;
                    }
                }
                w.flush()?;
                println!("posições gravadas em {}", path.display());
            }

            let last = states.last().expect("janela não vazia");
            let multiple = last.value / last.contributed_cum;
            println!(
                "{}: {} meses | aportado R$ {:.2} | patrimônio R$ {:.2} | {:.2}x o aportado",
                s.name, states.len(), last.contributed_cum, last.value, multiple
            );
        }
    }
    Ok(())
}
