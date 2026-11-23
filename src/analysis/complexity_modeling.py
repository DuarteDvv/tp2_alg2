"""modelagem de complexidade empírica temporal e espacial por regressão."""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score, root_mean_squared_error

from .data_loader import DEFAULT_MEMORIA_PATH, DEFAULT_OUTPUT_DIR, DEFAULT_TEMPOS_PATH, load_datasets


def linear_model(x, a, b):
    return a * x + b


def n_log_n_model(x, a, b):
    return a * x * np.log2(x) + b


def quadratic_model(x, a, b):
    return a * (x ** 2) + b


def quadratic_poly_model(x, a, b, c):
    return a * (x ** 2) + b * x + c


def cubic_model(x, a, b):
    return a * (x ** 3) + b


@dataclass(frozen=True)
class RegressionSpec:
    category: str
    subroutine: str
    x_label: str
    x_col: str
    y_col: str
    theoretical_complexity: str
    model_fn: object
    param_names: tuple
    filter_fn: object = None
    log10_y: bool = False
    unit_scale: float = 1.0


def filter_strategy(strategy):
    return lambda df: df[df["strategy"] == strategy]


def filter_optimal(strategy=None):
    def _filter(df):
        subset = df[df["status"] == "optimal"]
        return subset[subset["strategy"] == strategy] if strategy else subset

    return _filter


def filter_unique_instances(strategy="hull"):
    # cada instância compartilha a mesma geometria e matriz entre estratégias.
    return filter_strategy(strategy)


def fit_regression(dataframe, spec):
    """ajusta um modelo teórico aos dados filtrados e calcula R2 e RMSE."""

    subset = spec.filter_fn(dataframe) if spec.filter_fn else dataframe
    subset = subset[[spec.x_col, spec.y_col]].dropna()
    x_values = subset[spec.x_col].to_numpy(dtype=float)
    y_values = subset[spec.y_col].to_numpy(dtype=float) * spec.unit_scale
    if spec.log10_y:
        valid = y_values > 0
        x_values = x_values[valid]
        y_values = np.log10(y_values[valid])

    params, _ = curve_fit(spec.model_fn, x_values, y_values, maxfev=10000)
    y_pred = spec.model_fn(x_values, *params)
    r2 = float(r2_score(y_values, y_pred))
    rmse = float(root_mean_squared_error(y_values, y_pred))
    param_dict = {name: float(val) for name, val in zip(spec.param_names, params)}

    return {
        "record": {
            "category": spec.category,
            "subroutine": spec.subroutine,
            "x_variable": spec.x_label,
            "y_column": spec.y_col,
            "theoretical_complexity": spec.theoretical_complexity,
            "samples": int(len(x_values)),
            "parameters": json.dumps(param_dict),
            "r2": r2,
            "rmse": rmse,
        },
        "x": x_values,
        "y": y_values,
        "params": params,
        "spec": spec,
    }


TIME_SPECS = (
    RegressionSpec(
        "tempo", "Matriz de Distâncias", "N", "size", "matrix_seconds",
        "Theta(N^2)", quadratic_poly_model, ("a", "b", "c"),
        filter_fn=filter_unique_instances("hull"), unit_scale=1e3,
    ),
    RegressionSpec(
        "tempo", "Vizinho Mais Próximo", "N", "size", "initial_seconds",
        "Theta(N^2)", quadratic_model, ("a", "b"),
        filter_fn=filter_strategy("nearest"), unit_scale=1e3,
    ),
    RegressionSpec(
        "tempo", "Fecho Convexo (Monotone Chain)", "N", "size", "hull_seconds",
        "Theta(N log N)", n_log_n_model, ("a", "b"),
        filter_fn=filter_strategy("hull"), unit_scale=1e3,
    ),
    RegressionSpec(
        "tempo", "Inserção Gulosa no Fecho", "N", "size", "insertion_seconds",
        "Theta(N^3)", cubic_model, ("a", "b"),
        filter_fn=filter_strategy("hull"), unit_scale=1e3,
    ),
    RegressionSpec(
        "tempo", "MST Inicial (Prim Denso)", "N", "size", "mst_seconds",
        "Theta(N^2)", quadratic_model, ("a", "b"),
        filter_fn=filter_strategy("twice"), unit_scale=1e3,
    ),
    RegressionSpec(
        "tempo", "MST por Chamada no B&B", "N", "size", "search_mst_per_call_seconds",
        "O(N^2)", quadratic_model, ("a", "b"),
        filter_fn=filter_unique_instances("hull"), unit_scale=1e3,
    ),
    RegressionSpec(
        "tempo", "Matching Mínimo vs |O|", "|O|", "mst_odd_vertices", "matching_seconds",
        "O(|O|^3)", cubic_model, ("a", "b"),
        filter_fn=filter_strategy("christofides"), unit_scale=1e3,
    ),
    RegressionSpec(
        "tempo", "Matching Mínimo vs N", "N", "size", "matching_seconds",
        "O(N^3)", cubic_model, ("a", "b"),
        filter_fn=filter_strategy("christofides"), unit_scale=1e3,
    ),
    RegressionSpec(
        "tempo", "Circuito Euleriano (Hierholzer)", "N", "size", "euler_seconds",
        "Theta(N)", linear_model, ("a", "b"),
        filter_fn=filter_strategy("twice"), unit_scale=1e3,
    ),
    RegressionSpec(
        "tempo", "B&B Exato (log10 T vs N)", "N", "size", "search_seconds",
        "Exponencial (log10 T = aN + b)", linear_model, ("a", "b"),
        filter_fn=filter_optimal("hull"), log10_y=True,
    ),
    RegressionSpec(
        "tempo", "B&B Exato (T vs nós * N^2)", "nós * N^2", "search_work_proxy", "search_seconds",
        "Theta(nós * N^2)", linear_model, ("a", "b"),
        filter_fn=filter_optimal(),
    ),
)

MEMORY_SPECS = (
    RegressionSpec(
        "memoria", "Matriz de Distâncias (Todas)", "N", "size", "matrix_peak_bytes",
        "Theta(N^2)", quadratic_poly_model, ("a", "b", "c"),
        filter_fn=filter_unique_instances("hull"), unit_scale=1 / 1024,
    ),
    RegressionSpec(
        "memoria", "Matriz de Distâncias (sem st70)", "N", "size", "matrix_peak_bytes",
        "Theta(N^2)", quadratic_poly_model, ("a", "b", "c"),
        filter_fn=lambda df: df[(df["strategy"] == "hull") & (df["source_instance"] != "st70")],
        unit_scale=1 / 1024,
    ),
    RegressionSpec(
        "memoria", "Fecho Convexo (Monotone Chain)", "N", "size", "hull_peak_bytes",
        "Theta(N)", linear_model, ("a", "b"),
        filter_fn=filter_strategy("hull"), unit_scale=1 / 1024,
    ),
    RegressionSpec(
        "memoria", "Inserção Gulosa no Fecho", "N", "size", "insertion_peak_bytes",
        "Theta(N)", linear_model, ("a", "b"),
        filter_fn=filter_strategy("hull"), unit_scale=1 / 1024,
    ),
    RegressionSpec(
        "memoria", "MST Inicial (Prim Denso)", "N", "size", "mst_peak_bytes",
        "Theta(N)", linear_model, ("a", "b"),
        filter_fn=filter_strategy("twice"), unit_scale=1 / 1024,
    ),
    RegressionSpec(
        "memoria", "Matching Mínimo vs |O|", "|O|", "mst_odd_vertices", "matching_peak_bytes",
        "Theta(|O|^2)", quadratic_model, ("a", "b"),
        filter_fn=filter_strategy("christofides"), unit_scale=1 / 1024,
    ),
    RegressionSpec(
        "memoria", "Matching Mínimo vs N", "N", "size", "matching_peak_bytes",
        "O(N^2)", quadratic_model, ("a", "b"),
        filter_fn=filter_strategy("christofides"), unit_scale=1 / 1024,
    ),
    RegressionSpec(
        "memoria", "Circuito Euleriano (Hierholzer)", "N", "size", "euler_peak_bytes",
        "Theta(N)", linear_model, ("a", "b"),
        filter_fn=filter_strategy("twice"), unit_scale=1 / 1024,
    ),
    RegressionSpec(
        "memoria", "Busca B&B (DFS + MST por nível)", "N", "size", "search_mst_peak_bytes",
        "Theta(N)", linear_model, ("a", "b"),
        filter_fn=filter_unique_instances("hull"), unit_scale=1 / 1024,
    ),
)


def plot_fit_panel(ax, fit_result, title, y_label, annotate_points=None):
    """desenha os pontos empíricos e a curva ajustada em um eixo Matplotlib."""

    x = fit_result["x"]
    y = fit_result["y"]
    spec = fit_result["spec"]
    params = fit_result["params"]
    record = fit_result["record"]

    ax.scatter(x, y, color="#1f77b4", alpha=0.85, s=36, label="Empírico")
    x_grid = np.linspace(x.min(), x.max(), 200)
    y_grid = spec.model_fn(x_grid, *params)
    ax.plot(x_grid, y_grid, color="#d62728", linewidth=1.8,
            label=f"{spec.theoretical_complexity} ($R^2={record['r2']:.3f}$)")

    if annotate_points:
        for px, py, text in annotate_points:
            ax.annotate(text, (px, py), xytext=(-78, -14), textcoords="offset points",
                        fontsize=8, color="#333333",
                        arrowprops={"arrowstyle": "->", "lw": 0.8, "color": "#555555"})

    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.set_xlabel(spec.x_label, fontsize=9)
    ax.set_ylabel(y_label, fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend(fontsize=8, loc="best")


def save_figure(fig, output_dir, stem):
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(output_dir / f"{stem}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def generate_time_figure(fits_by_name, output_dir):
    """gera a figura de modelagem de complexidade temporal."""

    panels = [
        ("Matriz de Distâncias", "Matriz de Distâncias ($\\Theta(N^2)$)", "Tempo (ms)"),
        ("Inserção Gulosa no Fecho", "Inserção no Fecho ($\\Theta(N^3)$)", "Tempo (ms)"),
        ("MST por Chamada no B&B", "Prim por Chamada no B&B ($O(N^2)$)", "Tempo médio (ms)"),
        ("Matching Mínimo vs |O|", "Matching Blossom ($O(|O|^3)$)", "Tempo (ms)"),
        ("B&B Exato (log10 T vs N)", "B&B Exato: $\\log_{10} T(N)$", "$\\log_{10}$(Tempo em s)"),
        ("B&B Exato (T vs nós * N^2)", "B&B Exato: Trabalho por Nó", "Tempo de busca (s)"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 8.0))
    for ax, (name, title, ylabel) in zip(axes.flat, panels):
        plot_fit_panel(ax, fits_by_name[name], title, ylabel)

    save_figure(fig, output_dir, "fig_complexidade_tempo")


def generate_memory_figure(fits_by_name, memoria_df, output_dir):
    """gera a figura de complexidade espacial destacando distorções do CPython."""

    st70_row = memoria_df[(memoria_df["instance"] == "st70") & (memoria_df["strategy"] == "hull")].iloc[0]
    st70_note = [(float(st70_row["size"]), float(st70_row["matrix_peak_bytes"]) / 1024, "st70 (int cache)")]

    panels = [
        ("Matriz de Distâncias (Todas)", "Matriz de Distâncias ($\\Theta(N^2)$)", "Pico adicional (KiB)", st70_note),
        ("Matching Mínimo vs |O|", "Matching NetworkX ($\\Theta(|O|^2)$)", "Pico adicional (KiB)", None),
        ("Inserção Gulosa no Fecho", "Inserção no Fecho ($\\Theta(N)$)", "Pico adicional (KiB)", None),
        ("Busca B&B (DFS + MST por nível)", "Busca B&B In-Place ($\\Theta(N)$)", "Pico adicional (KiB)", None),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.5))
    for ax, (name, title, ylabel, notes) in zip(axes.flat, panels):
        plot_fit_panel(ax, fits_by_name[name], title, ylabel, annotate_points=notes)

    save_figure(fig, output_dir, "fig_complexidade_memoria")


def run_complexity_modeling(tempos_path=DEFAULT_TEMPOS_PATH, memoria_path=DEFAULT_MEMORIA_PATH,
                            output_dir=DEFAULT_OUTPUT_DIR):
    """executa todas as regressões temporais/espaciais e salva CSV e figuras."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tempos_df, memoria_df = load_datasets(tempos_path, memoria_path)

    time_fits = {spec.subroutine: fit_regression(tempos_df, spec) for spec in TIME_SPECS}
    memory_fits = {spec.subroutine: fit_regression(memoria_df, spec) for spec in MEMORY_SPECS}

    records = [fit["record"] for fit in time_fits.values()] + [fit["record"] for fit in memory_fits.values()]
    summary_df = pd.DataFrame(records)
    csv_path = output_dir / "regressao_complexidade.csv"
    summary_df.to_csv(csv_path, index=False)

    generate_time_figure(time_fits, output_dir)
    generate_memory_figure(memory_fits, memoria_df, output_dir)
    return summary_df, csv_path


def main():
    parser = argparse.ArgumentParser(description="Modelagem de complexidade empírica (Etapa 1).")
    parser.add_argument("--tempos", type=Path, default=DEFAULT_TEMPOS_PATH)
    parser.add_argument("--memoria", type=Path, default=DEFAULT_MEMORIA_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    summary_df, csv_path = run_complexity_modeling(args.tempos, args.memoria, args.output_dir)
    print(summary_df[["category", "subroutine", "x_variable", "theoretical_complexity", "samples", "r2", "rmse"]].to_string(index=False))
    print(f"\nTabela salva em: {csv_path}")


if __name__ == "__main__":
    main()
