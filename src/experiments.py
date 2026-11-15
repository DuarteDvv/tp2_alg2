"""Execução de experimentos e gravação incremental em CSV."""

import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
from time import perf_counter
import tracemalloc

import networkx as nx

from .branch_and_bound import branch_and_bound
from .heuristics import STRATEGIES, initial_route
from .instance import distance_matrix, read_instance
from .profiling import Profiler
from .routes import route_cost


STAGES = ("read", "matrix", "hull", "insertion", "mst", "matching", "euler")


def time_limit_arg(value):
    value = float(value)
    if not 0 < value <= 1800:
        raise argparse.ArgumentTypeError("Use um tempo maior que 0 e até 1800 segundos.")
    return value


def run_experiment(path, strategy, time_limit=1800, memory=False, initial_only=False):
    """Orçamento: leitura, matriz, warm-start e busca.

    Timeout cooperativo: checado antes da busca, a cada estado e durante
    Prim. A inicialização em biblioteca termina antes da checagem.
    """
    if not 0 < time_limit <= 1800:
        raise ValueError("Use um tempo maior que 0 e até 1800 segundos.")
    profile = Profiler(memory)
    if memory:
        tracemalloc.start()
    try:
        start = perf_counter()
        name, points = profile.measure("read", read_instance, path)
        distances = profile.measure("matrix", distance_matrix, points)
        warm_start = perf_counter()
        route = initial_route(strategy, distances, points, profile)
        cost = route_cost(route, distances)
        initial_seconds = perf_counter() - warm_start
        row = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "instance": name, "instance_path": str(path), "size": len(points),
            "strategy": strategy,
            "mode": "initial_only" if initial_only else "bnb",
            "time_limit_seconds": time_limit, "memory_tracing": memory,
            "python_version": platform.python_version(),
            "networkx_version": nx.__version__,
            "initial_seconds": initial_seconds,
        }
        if initial_only:
            row.update(status="heuristic", route=route, best_cost=cost,
                       initial_cost=cost, search_seconds=0, bound_seconds=0,
                       bound_calls=0, nodes_expanded=0, nodes_pruned=0,
                       complete_routes=0, max_depth=0)
            if perf_counter() - start >= time_limit:
                row["status"] = "timeout"
        else:
            remaining = max(0, time_limit - (perf_counter() - start))
            row.update(asdict(branch_and_bound(distances, route, remaining)))

        row["total_seconds"] = perf_counter() - start
        row["optimal_cost"] = row["best_cost"] if row["status"] == "optimal" else "NA"
        row["peak_bytes"] = (
            max(profile.peak_bytes, tracemalloc.get_traced_memory()[1]) if memory else "NA"
        )
        for stage in STAGES:
            row[stage + "_seconds"] = profile.metrics.get(stage + "_seconds", "NA")
            row[stage + "_peak_bytes"] = profile.metrics.get(stage + "_peak_bytes", "NA")
        if route_cost(row["route"], distances) != row["best_cost"]:
            raise ValueError("O custo retornado não corresponde à rota.")
        row["route"] = json.dumps(row["route"])
        return row
    finally:
        if memory:
            tracemalloc.stop()


def main():
    parser = argparse.ArgumentParser(description="Experimentos com as cinco inicializações.")
    parser.add_argument("instances", nargs="*", type=Path, help="Padrão: data/*.tsp")
    parser.add_argument("--strategies", nargs="+", choices=STRATEGIES, default=list(STRATEGIES))
    parser.add_argument("--time-limit", type=time_limit_arg, default=1800)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("results/bnb.csv"))
    parser.add_argument("--memory", action="store_true", help="Mede alocações Python com tracemalloc")
    parser.add_argument("--initial-only", action="store_true", help="Executa apenas as inicializações")
    args = parser.parse_args()
    paths = args.instances or sorted(Path("data").glob("*.tsp"))
    if not paths or args.repetitions < 1:
        parser.error("Informe instâncias e ao menos uma repetição.")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Append mantém as coletas anteriores. Cada resultado é descarregado
    # no arquivo antes da próxima execução demorada.
    with args.output.open("a+", newline="", encoding="utf-8") as file:
        file.seek(0)
        existing_header = next(csv.reader(file), None)
        file.seek(0, 2)
        writer = None
        for repetition in range(1, args.repetitions + 1):
            for path in paths:
                for strategy in args.strategies:
                    print(f"{path.stem} | {strategy} | repetição {repetition}", flush=True)
                    row = run_experiment(path, strategy, args.time_limit, args.memory, args.initial_only)
                    row["repetition"] = repetition
                    if writer is None:
                        if existing_header and existing_header != list(row):
                            raise ValueError("Cabeçalho incompatível: escolha outro arquivo de saída.")
                        writer = csv.DictWriter(file, fieldnames=list(row))
                        if not existing_header:
                            writer.writeheader()
                    writer.writerow(row)
                    file.flush()
                    print(f"  {row['status']} | custo {row['best_cost']} | {row['total_seconds']:.3f} s", flush=True)


if __name__ == "__main__":
    main()
