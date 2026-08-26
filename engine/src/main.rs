//! Motor de backtest.
//!
//! O motor não conhece gráficos nem interface: recebe uma estratégia e um dataset,
//! calcula, e devolve os estados da carteira.

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
        #[arg(long)]
        data: PathBuf,
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
        Command::Run { strategy, data } => {
            let s = load(&strategy)?;
            anyhow::bail!(
                "motor ainda não implementado: {} sobre {}",
                s.name,
                data.display()
            );
        }
    }
    Ok(())
}
