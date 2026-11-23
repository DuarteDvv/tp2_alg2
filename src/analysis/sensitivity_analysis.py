"""análise de sensibilidade topológica e identificação de instâncias adversariais."""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, root_mean_squared_error
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor, export_text

from .complexity_modeling import save_figure
from .data_loader import DEFAULT_OUTPUT_DIR, DEFAULT_TEMPOS_PATH, load_results_csv


FEATURE_COLUMNS = (
    "aspect_ratio",
    "hull_fraction",
    "spatial_entropy",
    "normalized_entropy",
    "mst_max_degree",
    "odd_fraction",
    "nearest_neighbor_cv",
    "mst_to_opt_ratio",
    "triangle_violations",
)

MODEL_FEATURES = (
    "aspect_ratio",
    "hull_fraction",
    "normalized_entropy",
    "mst_max_degree",
    "odd_fraction",
    "nearest_neighbor_cv",
    "mst_to_opt_ratio",
)

FEATURE_LABELS = {
    "aspect_ratio": "Aspect Ratio",
    "hull_fraction": "Hull Fraction",
    "spatial_entropy": "Spatial Entropy",
    "normalized_entropy": "Norm. Entropy",
    "mst_max_degree": "MST Max Degree",
    "odd_fraction": "MST Odd Fraction",
    "nearest_neighbor_cv": "Nearest Neighbor CV",
    "mst_to_opt_ratio": "MST / Opt Ratio",
    "triangle_violations": "Triangle Violations",
}

TARGET_COLUMNS = (
    "gap_nearest",
    "gap_hull",
    "gap_twice",
    "gap_christofides",
    "bnb_effort_per_city",
)

TARGET_LABELS = {
    "gap_nearest": "Gap Nearest (%)",
    "gap_hull": "Gap Hull (%)",
    "gap_twice": "Gap Twice (%)",
    "gap_christofides": "Gap Christofides (%)",
    "bnb_effort_per_city": "Esforço B&B (log10 nós / N)",
}


def build_instance_feature_table(tempos_df):
    """consolida uma linha por instância com features normalizadas, gaps e esforço do B&B."""

    base = tempos_df[tempos_df["strategy"] == "hull"].copy().set_index("instance")
    base["odd_fraction"] = base["mst_odd_vertices"] / base["size"]
    max_cells = np.minimum(base["size"], 16)
    base["normalized_entropy"] = base["spatial_entropy"] / np.log(max_cells)
    base["mst_to_opt_ratio"] = base["mst_cost"] / base["reference_cost"]
    base["bnb_effort_per_city"] = np.log10(np.maximum(base["nodes_expanded"], 1)) / base["size"]

    for strategy in ("nearest", "hull", "twice", "christofides"):
        strat_gaps = tempos_df[tempos_df["strategy"] == strategy].set_index("instance")["initial_gap_percent"]
        base[f"gap_{strategy}"] = strat_gaps

    ordered_cols = [
        "size", "weight_type", "dataset_group", "status",
        *FEATURE_COLUMNS, *TARGET_COLUMNS,
    ]
    return base[ordered_cols].reset_index().sort_values(["size", "instance"]).reset_index(drop=True)


def compute_correlations(instance_df):
    """calcula correlações de Pearson e Spearman entre cada feature e cada alvo."""

    records = []
    for feature in FEATURE_COLUMNS:
        x = instance_df[feature].to_numpy(dtype=float)
        for target in TARGET_COLUMNS:
            y = instance_df[target].to_numpy(dtype=float)
            p_corr, p_val = pearsonr(x, y)
            s_corr, s_val = spearmanr(x, y)
            records.append({
                "feature": feature,
                "feature_label": FEATURE_LABELS[feature],
                "target": target,
                "target_label": TARGET_LABELS[target],
                "pearson_r": float(p_corr),
                "pearson_pvalue": float(p_val),
                "spearman_rho": float(s_corr),
                "spearman_pvalue": float(s_val),
            })

    return pd.DataFrame(records)


def fit_sensitivity_models(instance_df):
    """ajusta regressão linear múltipla padronizada e árvore de decisão por alvo."""

    x_raw = instance_df[list(MODEL_FEATURES)].to_numpy(dtype=float)
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x_raw)

    records = []
    tree_rules = {}
    for target in TARGET_COLUMNS:
        y = instance_df[target].to_numpy(dtype=float)

        reg = LinearRegression()
        reg.fit(x_scaled, y)
        y_pred_reg = reg.predict(x_scaled)
        reg_r2 = float(r2_score(y, y_pred_reg))
        reg_rmse = float(root_mean_squared_error(y, y_pred_reg))
        y_std = float(np.std(y)) if np.std(y) > 0 else 1.0
        standardized_betas = reg.coef_ / y_std

        tree = DecisionTreeRegressor(max_depth=2, min_samples_leaf=2, random_state=42)
        tree.fit(x_raw, y)
        y_pred_tree = tree.predict(x_raw)
        tree_r2 = float(r2_score(y, y_pred_tree))
        tree_rmse = float(root_mean_squared_error(y, y_pred_tree))
        tree_rules[target] = export_text(tree, feature_names=list(MODEL_FEATURES))

        for feat_name, beta, importance in zip(MODEL_FEATURES, standardized_betas, tree.feature_importances_):
            records.append({
                "target": target,
                "target_label": TARGET_LABELS[target],
                "feature": feat_name,
                "feature_label": FEATURE_LABELS[feat_name],
                "standardized_beta": float(beta),
                "linear_r2": reg_r2,
                "linear_rmse": reg_rmse,
                "tree_importance": float(importance),
                "tree_r2": tree_r2,
                "tree_rmse": tree_rmse,
            })

    return pd.DataFrame(records), tree_rules


def plot_sensitivity_figure(instance_df, corr_df, model_df, output_dir):
    """gera painel 2x2 com heatmap de correlação, pesos das features e casos adversariais."""

    fig, axes = plt.subplots(2, 2, figsize=(14.0, 9.5))

    # Painel 1: Heatmap de correlação de Pearson.
    ax1 = axes[0, 0]
    pivot_corr = corr_df.pivot(index="feature", columns="target", values="pearson_r")
    pivot_corr = pivot_corr.loc[list(MODEL_FEATURES), list(TARGET_COLUMNS)]
    matrix = pivot_corr.to_numpy(dtype=float)
    im = ax1.imshow(matrix, cmap="coolwarm", vmin=-1.0, vmax=1.0, aspect="auto")

    ax1.set_xticks(np.arange(len(TARGET_COLUMNS)))
    ax1.set_xticklabels([TARGET_LABELS[t].replace(" (%)", "") for t in TARGET_COLUMNS],
                        rotation=25, ha="right", fontsize=8)
    ax1.set_yticks(np.arange(len(MODEL_FEATURES)))
    ax1.set_yticklabels([FEATURE_LABELS[f] for f in MODEL_FEATURES], fontsize=8)
    for row_idx in range(matrix.shape[0]):
        for col_idx in range(matrix.shape[1]):
            val = matrix[row_idx, col_idx]
            text_color = "white" if abs(val) > 0.55 else "#111111"
            ax1.text(col_idx, row_idx, f"{val:.2f}", ha="center", va="center",
                     color=text_color, fontsize=8, fontweight="bold")

    fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.04, label="Pearson $r$")
    ax1.set_title("Correlação de Pearson (Features vs. Gaps e Esforço B&B)", fontsize=10, fontweight="bold")

    # Painel 2: Importância das features na Árvore de Decisão (max_depth=2).
    ax2 = axes[0, 1]
    pivot_imp = model_df.pivot(index="feature", columns="target", values="tree_importance")
    pivot_imp = pivot_imp.loc[list(MODEL_FEATURES), list(TARGET_COLUMNS)]
    y_pos = np.arange(len(MODEL_FEATURES))
    bar_height = 0.15
    target_colors = ["#ff7f0e", "#2ca02c", "#9467bd", "#1f77b4", "#d62728"]
    for idx, (target, color) in enumerate(zip(TARGET_COLUMNS, target_colors)):
        offset = (idx - 2.0) * bar_height
        ax2.barh(y_pos + offset, pivot_imp[target].to_numpy(), height=bar_height,
                 color=color, alpha=0.9, label=TARGET_LABELS[target].replace(" (%)", ""))

    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([FEATURE_LABELS[f] for f in MODEL_FEATURES], fontsize=8)
    ax2.invert_yaxis()
    ax2.set_xlim(0, 0.92)
    ax2.set_xlabel("Importância na Árvore de Decisão (Gini / MSE reduction)", fontsize=9)
    ax2.set_title("Peso das Features por Algoritmo (Árvore de Decisão)", fontsize=10, fontweight="bold")
    ax2.grid(True, axis="x", linestyle="--", alpha=0.35)
    ax2.legend(fontsize=7.5, loc="center right")

    # Painel 3: Sensibilidade do Fecho Convexo (Hull Fraction) e Christofides (Entropia).
    ax3 = axes[1, 0]
    x_hull = instance_df["hull_fraction"].to_numpy()
    y_hull = instance_df["gap_hull"].to_numpy()
    ax3.scatter(x_hull, y_hull, color="#2ca02c", s=45, alpha=0.85, label="Gap Hull vs. Hull Fraction")
    slope_h, intercept_h = np.polyfit(x_hull, y_hull, 1)
    x_line = np.linspace(x_hull.min(), x_hull.max(), 100)
    ax3.plot(x_line, slope_h * x_line + intercept_h, color="#2ca02c", linestyle="--", linewidth=1.5)

    for _, row in instance_df[instance_df["instance"].isin(["berlin52", "st70", "att48_sub10", "ulysses22.tsp"])].iterrows():
        label = row["instance"].replace(".tsp", "").replace("_sub", "-")
        dx = -44 if label == "att48-10" else 5
        ax3.annotate(label, (row["hull_fraction"], row["gap_hull"]),
                     xytext=(dx, 4), textcoords="offset points", fontsize=7.5, color="#1b611b")

    ax3_twin = ax3.twinx()
    x_odd = instance_df["odd_fraction"].to_numpy()
    y_ch = instance_df["gap_christofides"].to_numpy()
    ax3_twin.scatter(x_odd, y_ch, color="#1f77b4", marker="^", s=45, alpha=0.85,
                     label="Gap Christofides vs. Odd Fraction")
    slope_c, intercept_c = np.polyfit(x_odd, y_ch, 1)
    x_line_c = np.linspace(x_odd.min(), x_odd.max(), 100)
    ax3_twin.plot(x_line_c, slope_c * x_line_c + intercept_c, color="#1f77b4", linestyle=":", linewidth=1.5)

    ax3.set_title("Sensibilidade Geométrica: Hull Fraction e Vértices Ímpares", fontsize=10, fontweight="bold")
    ax3.set_xlabel("Proporção de vértices (Hull Fraction / MST Odd Fraction)", fontsize=9)
    ax3.set_ylabel("Gap Convex Hull (%)", color="#2ca02c", fontsize=9)
    ax3_twin.set_ylabel("Gap Christofides (%)", color="#1f77b4", fontsize=9)
    ax3.grid(True, linestyle="--", alpha=0.35)

    lines_1, labels_1 = ax3.get_legend_handles_labels()
    lines_2, labels_2 = ax3_twin.get_legend_handles_labels()
    ax3.legend(lines_1 + lines_2, labels_1 + labels_2, fontsize=7.5, loc="upper right")

    # Painel 4: Instâncias Adversariais (Nearest Neighbor CV vs. Esforço B&B e Gap Nearest).
    ax4 = axes[1, 1]
    cv_vals = instance_df["nearest_neighbor_cv"].to_numpy()
    bnb_vals = instance_df["bnb_effort_per_city"].to_numpy()
    nn_gaps = instance_df["gap_nearest"].to_numpy()
    scatter = ax4.scatter(cv_vals, bnb_vals, c=nn_gaps, cmap="plasma", s=65, edgecolors="#333333", linewidth=0.7)
    fig.colorbar(scatter, ax=ax4, fraction=0.046, pad=0.04, label="Gap Nearest Neighbor (%)")

    for _, row in instance_df.iterrows():
        name = row["instance"].replace(".tsp", "").replace("_sub", "-")
        if name in ("ulysses16", "ulysses22", "st70-16", "att48-26", "att48-34", "st70", "burma14"):
            dx = -52 if "ulysses22" in name else 6
            dy = -10 if "ulysses16" in name else 4
            ax4.annotate(name, (row["nearest_neighbor_cv"], row["bnb_effort_per_city"]),
                         xytext=(dx, dy), textcoords="offset points", fontsize=8,
                         fontweight="bold" if "ulysses" in name else "normal")

    ax4.set_title("Instâncias Adversariais: Heterogeneidade Local (CV) vs. Colapso B&B", fontsize=10, fontweight="bold")
    ax4.set_xlabel("Coeficiente de Variação do Vizinho Mais Próximo (CV)", fontsize=9)
    ax4.set_ylabel("Esforço B&B ($\\log_{10}(\\text{nós expandidos}) / N$)", fontsize=9)
    ax4.grid(True, linestyle="--", alpha=0.35)

    save_figure(fig, output_dir, "fig_sensibilidade_features")


def run_sensitivity_analysis(tempos_path=DEFAULT_TEMPOS_PATH, output_dir=DEFAULT_OUTPUT_DIR):
    """executa a análise de sensibilidade completa e salva tabelas e gráficos."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tempos_df = load_results_csv(tempos_path)

    instance_df = build_instance_feature_table(tempos_df)
    corr_df = compute_correlations(instance_df)
    model_df, tree_rules = fit_sensitivity_models(instance_df)

    inst_csv = output_dir / "instancias_sensibilidade.csv"
    corr_csv = output_dir / "correlacoes_sensibilidade.csv"
    model_csv = output_dir / "importancia_features.csv"
    rules_txt = output_dir / "regras_arvore_decisao.txt"

    instance_df.to_csv(inst_csv, index=False)
    corr_df.to_csv(corr_csv, index=False)
    model_df.to_csv(model_csv, index=False)

    rules_content = "\n".join(
        f"=== {TARGET_LABELS[target]} ({target}) ===\n{rules}"
        for target, rules in tree_rules.items()
    )
    rules_txt.write_text(rules_content, encoding="utf-8")

    plot_sensitivity_figure(instance_df, corr_df, model_df, output_dir)
    return instance_df, corr_df, model_df, tree_rules


def main():
    parser = argparse.ArgumentParser(description="Análise de sensibilidade e instâncias adversariais (Etapa 3).")
    parser.add_argument("--tempos", type=Path, default=DEFAULT_TEMPOS_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    _, corr_df, model_df, tree_rules = run_sensitivity_analysis(args.tempos, args.output_dir)

    print("=== Maiores Correlações de Pearson por Alvo ===")
    for target in TARGET_COLUMNS:
        sub = corr_df[corr_df["target"] == target].reindex(
            corr_df[corr_df["target"] == target]["pearson_r"].abs().sort_values(ascending=False).index
        )
        top = sub.iloc[0]
        second = sub.iloc[1]
        print(f"{TARGET_LABELS[target]:30}: 1) {top['feature']} (r={top['pearson_r']:+.3f}, rho={top['spearman_rho']:+.3f}) | "
              f"2) {second['feature']} (r={second['pearson_r']:+.3f}, rho={second['spearman_rho']:+.3f})")

    print("\n=== Desempenho dos Modelos (Regressão Múltipla vs. Árvore de Decisão) ===")
    summary_models = model_df.groupby(["target", "target_label"], as_index=False).first()[
        ["target_label", "linear_r2", "linear_rmse", "tree_r2", "tree_rmse"]
    ]
    print(summary_models.to_string(index=False))

    print("\n=== Regras das Árvores de Decisão (max_depth=2) ===")
    for target, rules in tree_rules.items():
        print(f"--- {TARGET_LABELS[target]} ---")
        print(rules.strip())


if __name__ == "__main__":
    main()
