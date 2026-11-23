"""carregamento e preparação dos CSVs de experimentos."""

from pathlib import Path
import pandas as pd


DEFAULT_TEMPOS_PATH = Path("results/tempos.csv")
DEFAULT_MEMORIA_PATH = Path("results/memoria.csv")
DEFAULT_OUTPUT_DIR = Path("results/modelagem")


def load_results_csv(path):
    """lê um CSV de resultados convertendo 'NA' para NaN e ordenando por tamanho."""

    dataframe = pd.read_csv(path, na_values=["NA"], keep_default_na=True)
    dataframe["size"] = dataframe["size"].astype(int)
    if "search_mst_calls" in dataframe.columns and "search_mst_seconds" in dataframe.columns:
        valid_calls = dataframe["search_mst_calls"].where(dataframe["search_mst_calls"] > 0)
        dataframe["search_mst_per_call_seconds"] = dataframe["search_mst_seconds"] / valid_calls

    if "nodes_visited" in dataframe.columns:
        dataframe["search_work_proxy"] = dataframe["nodes_visited"] * (dataframe["size"] ** 2)

    return dataframe.sort_values(["size", "instance", "strategy"]).reset_index(drop=True)


def load_datasets(tempos_path=DEFAULT_TEMPOS_PATH, memoria_path=DEFAULT_MEMORIA_PATH):
    """carrega os conjuntos de tempo e memória."""

    return load_results_csv(tempos_path), load_results_csv(memoria_path)
