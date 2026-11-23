"""análise do impacto do warm-start na poda e no tempo do branch-and-bound."""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .complexity_modeling import save_figure
from .data_loader import DEFAULT_OUTPUT_DIR, DEFAULT_TEMPOS_PATH, load_results_csv


STRATEGY_ORDER = ("trivial", "nearest", "twice", "christofides", "hull")
STRATEGY_LABELS = {
    "trivial": "Trivial",
    "nearest": "Nearest Neighbor",
    "twice": "Twice-around-tree",
    "christofides": "Christofides",
    "hull": "Convex Hull + Ins.",
}
STRATEGY_COLORS = {
    "trivial": "#7f7f7f",
    "nearest": "#ff7f0e",
    "twice": "#9467bd",
    "christofides": "#1f77b4",
    "hull": "#2ca02c",
}


def build_warm_start_table(tempos_df):
    """calcula métricas de poda, redução de nós e ganho líquido frente ao trivial."""

    df = tempos_df.copy()
    df["pruning_ratio"] = np.where(
        df["nodes_visited"] > 0,
        df["nodes_pruned"] / df["nodes_visited"],
        0.0,
    )

    trivial_baselines = (
        df[df["strategy"] == "trivial"]
        .set_index("instance")[["nodes_expanded", "nodes_pruned", "search_seconds", "total_seconds"]]
        .rename(columns={
            "nodes_expanded": "trivial_nodes_expanded",
            "nodes_pruned": "trivial_nodes_pruned",
            "search_seconds": "trivial_search_seconds",
            "total_seconds": "trivial_total_seconds",
        })
    )
    df = df.join(trivial_baselines, on="instance")

    df["expanded_diff_vs_trivial"] = df["trivial_nodes_expanded"] - df["nodes_expanded"]
    df["expanded_reduction_percent"] = np.where(
        df["trivial_nodes_expanded"] > 0,
        100.0 * df["expanded_diff_vs_trivial"] / df["trivial_nodes_expanded"],
        0.0,
    )
    df["search_time_saved_seconds"] = df["trivial_search_seconds"] - df["search_seconds"]
    # desconta o custo da heurística inicial para avaliar o trade-off líquido.
    df["net_time_saved_seconds"] = df["search_time_saved_seconds"] - df["initial_seconds"]
    df["speedup_vs_trivial"] = np.where(
        df["total_seconds"] > 0,
        df["trivial_total_seconds"] / df["total_seconds"],
        1.0,
    )

    columns = [
        "instance", "size", "weight_type", "dataset_group", "strategy", "status",
        "initial_cost", "reference_cost", "initial_gap_percent", "best_cost", "best_gap_percent",
        "initial_seconds", "search_seconds", "total_seconds",
        "nodes_visited", "nodes_expanded", "nodes_pruned", "pruning_ratio",
        "expanded_diff_vs_trivial", "expanded_reduction_percent",
        "search_time_saved_seconds", "net_time_saved_seconds", "speedup_vs_trivial",
    ]
    strategy_rank = {name: idx for idx, name in enumerate(STRATEGY_ORDER)}
    df["_rank"] = df["strategy"].map(strategy_rank)
    df = df.sort_values(["size", "instance", "_rank"]).drop(columns=["_rank"]).reset_index(drop=True)
    return df[columns]


def build_strategy_aggregate(warm_df):
    """agrega indicadores médios e acumulados por estratégia de inicialização."""

    optimal_df = warm_df[warm_df["status"] == "optimal"]
    records = []
    for strategy in STRATEGY_ORDER:
        strat_all = warm_df[warm_df["strategy"] == strategy]
        strat_opt = optimal_df[optimal_df["strategy"] == strategy]
        records.append({
            "strategy": strategy,
            "mean_initial_gap_all_percent": float(strat_all["initial_gap_percent"].mean()),
            "median_initial_gap_all_percent": float(strat_all["initial_gap_percent"].median()),
            "mean_best_gap_timeout_percent": float(
                strat_all[strat_all["status"] == "timeout"]["best_gap_percent"].mean()
            ),
            "mean_initial_ms_all": float(strat_all["initial_seconds"].mean() * 1e3),
            "max_initial_ms_all": float(strat_all["initial_seconds"].max() * 1e3),
            "mean_expanded_reduction_optimal_percent": float(strat_opt["expanded_reduction_percent"].mean()),
            "max_expanded_reduction_optimal_percent": float(strat_opt["expanded_reduction_percent"].max()),
            "total_expanded_nodes_optimal": int(strat_opt["nodes_expanded"].sum()),
            "total_search_time_optimal_seconds": float(strat_opt["search_seconds"].sum()),
            "total_net_time_saved_optimal_seconds": float(strat_opt["net_time_saved_seconds"].sum()),
            "mean_speedup_optimal": float(strat_opt["speedup_vs_trivial"].mean()),
        })

    return pd.DataFrame(records)


def parse_depth_vector(row, column):
    values = json.loads(row[column])
    return np.asarray(values, dtype=float)


def plot_warm_start_figure(tempos_df, warm_df, output_dir):
    """gera figura 2x2 com redução de nós, gaps iniciais e perfis por profundidade."""

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.0))

    # Painel 1: Redução de nós expandidos (%) nas instâncias ótimas com maior busca.
    ax1 = axes[0, 0]
    featured_instances = ["att48_sub10", "berlin52_sub14", "burma14", "st70_sub16", "att48_sub18",
                          "berlin52_sub20", "st70_sub24", "att48_sub26", "st70_sub30", "att48_sub34"]
    sub_opt = warm_df[warm_df["instance"].isin(featured_instances)]
    x_pos = np.arange(len(featured_instances))
    bar_strategies = ("nearest", "twice", "christofides", "hull")
    width = 0.2
    for idx, strategy in enumerate(bar_strategies):
        vals = [
            float(sub_opt[(sub_opt["instance"] == inst) & (sub_opt["strategy"] == strategy)]["expanded_reduction_percent"].iloc[0])
            for inst in featured_instances
        ]
        offset = (idx - 1.5) * width
        ax1.bar(x_pos + offset, vals, width=width, color=STRATEGY_COLORS[strategy],
                label=STRATEGY_LABELS[strategy], alpha=0.9)

    ax1.set_title("Redução de Nós Expandidos vs. Trivial (Instâncias Ótimas)", fontsize=10, fontweight="bold")
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels([inst.replace("_sub", "-") for inst in featured_instances], rotation=30, ha="right", fontsize=8)
    ax1.set_ylabel("Redução de nós expandidos (%)", fontsize=9)
    ax1.grid(True, axis="y", linestyle="--", alpha=0.35)
    ax1.legend(fontsize=8, loc="upper right")

    # Painel 2: Qualidade do limite superior inicial (Gap %) vs. Tempo inicial (ms).
    ax2 = axes[0, 1]
    for strategy in STRATEGY_ORDER:
        sub = warm_df[warm_df["strategy"] == strategy]
        ax2.scatter(
            sub["initial_seconds"] * 1e3,
            sub["initial_gap_percent"],
            color=STRATEGY_COLORS[strategy],
            label=STRATEGY_LABELS[strategy],
            s=42, alpha=0.85,
        )
    ax2.set_xscale("log")
    ax2.set_yscale("symlog", linthresh=1.0)
    ax2.set_ylim(-0.15, 600)
    ax2.set_title("Trade-off na Inicialização: Tempo (ms) vs. Gap Inicial (%)", fontsize=10, fontweight="bold")
    ax2.set_xlabel("Tempo da heurística inicial (ms, escala log)", fontsize=9)
    ax2.set_ylabel("Gap inicial em relação ao ótimo (%, symlog)", fontsize=9)
    ax2.grid(True, linestyle="--", alpha=0.35)
    ax2.legend(fontsize=8, loc="best")

    # Painéis 3 e 4: Perfis por profundidade em att48_sub34 (N=34).
    target_instance = "att48_sub34"
    inst_rows = tempos_df[tempos_df["instance"] == target_instance].set_index("strategy")
    ax3 = axes[1, 0]
    ax4 = axes[1, 1]
    for strategy in ("trivial", "christofides", "hull"):
        row = inst_rows.loc[strategy]
        expanded = parse_depth_vector(row, "expanded_by_depth")
        pruned = parse_depth_vector(row, "pruned_by_depth")
        depths = np.arange(len(expanded))
        ax3.plot(depths, expanded / 1e3, color=STRATEGY_COLORS[strategy],
                 linewidth=1.8, marker="o", markersize=3, label=STRATEGY_LABELS[strategy])
        ax4.plot(depths, pruned / 1e6, color=STRATEGY_COLORS[strategy],
                 linewidth=1.8, marker="s", markersize=3, label=STRATEGY_LABELS[strategy])

    ax3.set_title(f"Perfil de Nós Expandidos por Profundidade ({target_instance})", fontsize=10, fontweight="bold")
    ax3.set_xlabel("Profundidade na árvore DFS", fontsize=9)
    ax3.set_ylabel("Nós expandidos ($\\times 10^3$)", fontsize=9)
    ax3.grid(True, linestyle="--", alpha=0.35)
    ax3.legend(fontsize=8, loc="upper right")

    ax4.set_title(f"Perfil de Nós Podados por Profundidade ({target_instance})", fontsize=10, fontweight="bold")
    ax4.set_xlabel("Profundidade na árvore DFS", fontsize=9)
    ax4.set_ylabel("Nós podados ($\\times 10^6$)", fontsize=9)
    ax4.grid(True, linestyle="--", alpha=0.35)
    ax4.legend(fontsize=8, loc="upper right")

    save_figure(fig, output_dir, "fig_warm_start_poda")


def run_warm_start_analysis(tempos_path=DEFAULT_TEMPOS_PATH, output_dir=DEFAULT_OUTPUT_DIR):
    """executa a avaliação do warm-start e salva tabelas e gráficos."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tempos_df = load_results_csv(tempos_path)

    warm_df = build_warm_start_table(tempos_df)
    aggregate_df = build_strategy_aggregate(warm_df)

    warm_csv = output_dir / "resumo_warm_start.csv"
    agg_csv = output_dir / "agregado_warm_start.csv"
    warm_df.to_csv(warm_csv, index=False)
    aggregate_df.to_csv(agg_csv, index=False)

    plot_warm_start_figure(tempos_df, warm_df, output_dir)
    return warm_df, aggregate_df, warm_csv, agg_csv


def main():
    parser = argparse.ArgumentParser(description="Análise do impacto do warm-start (Etapa 2).")
    parser.add_argument("--tempos", type=Path, default=DEFAULT_TEMPOS_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    _, aggregate_df, warm_csv, agg_csv = run_warm_start_analysis(args.tempos, args.output_dir)
    print(aggregate_df.to_string(index=False))
    print(f"\nTabelas salvas em:\n  {warm_csv}\n  {agg_csv}")


if __name__ == "__main__":
    main()
