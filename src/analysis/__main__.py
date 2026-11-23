"""executa o pipeline completo de modelagem, warm-start e sensibilidade."""

import argparse
from pathlib import Path

from .complexity_modeling import run_complexity_modeling
from .data_loader import DEFAULT_MEMORIA_PATH, DEFAULT_OUTPUT_DIR, DEFAULT_TEMPOS_PATH
from .sensitivity_analysis import run_sensitivity_analysis
from .warm_start_analysis import run_warm_start_analysis


def run_all_analyses(tempos_path=DEFAULT_TEMPOS_PATH, memoria_path=DEFAULT_MEMORIA_PATH,
                     output_dir=DEFAULT_OUTPUT_DIR):
    """executa as três etapas de modelagem e avaliação em sequência."""

    complexity_df, _ = run_complexity_modeling(tempos_path, memoria_path, output_dir)
    _, warm_agg_df, _, _ = run_warm_start_analysis(tempos_path, output_dir)
    _, corr_df, model_df, _ = run_sensitivity_analysis(tempos_path, output_dir)
    return {
        "complexity": complexity_df,
        "warm_start": warm_agg_df,
        "correlations": corr_df,
        "sensitivity_models": model_df,
    }


def main():
    parser = argparse.ArgumentParser(description="Executa toda a modelagem e avaliação do TP2.")
    parser.add_argument("--tempos", type=Path, default=DEFAULT_TEMPOS_PATH)
    parser.add_argument("--memoria", type=Path, default=DEFAULT_MEMORIA_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    run_all_analyses(args.tempos, args.memoria, args.output_dir)
    print(f"Pipeline concluído. Artefatos gerados em: {args.output_dir}")


if __name__ == "__main__":
    main()
