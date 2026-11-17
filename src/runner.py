"""Uma execução, com orçamento de tempo e coleta das métricas."""

from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
import tracemalloc

from .branch_and_bound import branch_and_bound
from .features import FEATURE_FIELDS, instance_features
from .heuristics import STRATEGIES, initial_route
from .instance import distance_matrix, file_hash, planar_points, read_instance, reference_cost
from .profiling import STAGES, create_profile, measure
from .routes import route_cost
from .timeout import execution_timeout


SEARCH_FIELDS = (
    "search_seconds", "bound_seconds", "bound_calls", "nodes_visited",
    "nodes_expanded", "nodes_pruned", "nodes_interrupted", "complete_routes", "max_depth",
)
RESULT_FIELDS = (
    "timestamp_utc", "instance", "instance_path", "instance_sha256", "source_instance",
    "dataset_group", "size", "weight_type", "strategy", "mode", "time_limit_seconds",
    "memory_tracing",
    "status", "timeout_stage", "initial_completed", "initial_seconds", "initial_cost",
    "initial_route", "best_cost", "route", *SEARCH_FIELDS, "expanded_by_depth",
    "pruned_by_depth", "total_seconds", "peak_bytes", "optimal_cost", "reference_cost",
    "reference_source", "initial_gap_percent", "best_gap_percent",
    *(stage + "_" + suffix for stage in STAGES for suffix in ("seconds", "calls", "peak_bytes")),
    *FEATURE_FIELDS, "feature_seconds",
)


def gap_percent(cost, optimum):
    if cost == "NA" or optimum == "NA":
        return "NA"
    if optimum == 0:
        return 0 if cost == 0 else "NA"
    return 100 * (cost - optimum) / optimum


def run_experiment(path, strategy, time_limit=1800, memory=False, initial_only=False):
    if time_limit is not None and not 0 < time_limit <= 1800:
        raise ValueError("Use um tempo maior que 0 e até 1800 segundos.")
    if strategy not in STRATEGIES:
        raise ValueError("Estratégia desconhecida.")
    path = Path(path)
    row = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "instance": path.stem, "instance_path": str(path),
        "instance_sha256": file_hash(path),
        "source_instance": path.stem.split("_sub")[0],
        "dataset_group": path.parent.name,
        "size": "NA", "weight_type": "NA", "strategy": strategy,
        "mode": "initial_only" if initial_only else "bnb",
        "time_limit_seconds": time_limit if time_limit is not None else "unlimited", "memory_tracing": memory,
        "status": "timeout", "timeout_stage": "NA",
        "initial_completed": False, "initial_seconds": "NA",
        "initial_cost": "NA", "initial_route": "NA",
        "best_cost": "NA", "route": "NA",
        **dict.fromkeys(SEARCH_FIELDS, 0),
        "expanded_by_depth": [], "pruned_by_depth": [],
    }
    profile = create_profile(memory)
    points = None
    geometry_points = None
    distances = None
    current_stage = "read"
    if memory:
        tracemalloc.start()
    start_time = perf_counter()
    try:
        remaining_seconds = time_limit - (perf_counter() - start_time) if time_limit is not None else None
        if remaining_seconds is not None and remaining_seconds <= 0:
            raise TimeoutError
        with execution_timeout(remaining_seconds):
            name, points, weight_type = measure(profile, "read", read_instance, path)
            row.update(instance=name, size=len(points), weight_type=weight_type)
            current_stage = "matrix"
            distances = measure(profile, "matrix", distance_matrix, points, weight_type)
            # Rota viável de reserva, caso a inicialização seja interrompida.
            fallback_route = list(range(len(points)))
            row.update(route=fallback_route, best_cost=route_cost(fallback_route, distances))
            geometry_points = planar_points(points, weight_type)
            current_stage = "initial"
            initial_start = perf_counter()
            try:
                route = initial_route(strategy, distances, geometry_points, profile)
                initial_cost = route_cost(route, distances)
            finally:
                row["initial_seconds"] = perf_counter() - initial_start
            row.update(initial_completed=True, initial_cost=initial_cost,
                       initial_route=route, route=route, best_cost=initial_cost)
            if initial_only:
                row["status"] = "heuristic"
        if not initial_only:
            # A busca verifica seu próprio prazo e devolve os resultados parciais.
            # O alarme externo poderia interromper essa devolução e perdê-los.
            current_stage = "search"
            remaining_seconds = max(0, time_limit - (perf_counter() - start_time)) if time_limit is not None else None
            row.update(branch_and_bound(distances, route, remaining_seconds, profile))
            if row["status"] == "timeout":
                row["timeout_stage"] = "search"
    except TimeoutError:
        row["status"] = "timeout"
        row["timeout_stage"] = current_stage
    finally:
        row["total_seconds"] = perf_counter() - start_time
        row["peak_bytes"] = "NA"
        if memory:
            row["peak_bytes"] = max(profile["peak_bytes"], tracemalloc.get_traced_memory()[1])
            tracemalloc.stop()

    published_optimum = reference_cost(path, distances) if distances is not None else "NA"
    row["optimal_cost"] = row["best_cost"] if row["status"] == "optimal" else "NA"
    row["reference_cost"] = published_optimum
    row["reference_source"] = "opt.tour" if published_optimum != "NA" else "NA"
    if row["status"] == "optimal":
        if published_optimum != "NA" and row["best_cost"] != published_optimum:
            raise ValueError("O ótimo encontrado difere da referência publicada.")
        if published_optimum == "NA":
            row["reference_cost"] = row["best_cost"]
            row["reference_source"] = "branch_and_bound"
    if (published_optimum != "NA" and row["best_cost"] != "NA"
            and row["best_cost"] < published_optimum):
        raise ValueError("Foi encontrado custo inferior ao ótimo publicado: confira as distâncias.")
    row["initial_gap_percent"] = gap_percent(row["initial_cost"], row["reference_cost"])
    row["best_gap_percent"] = gap_percent(row["best_cost"], row["reference_cost"])

    for stage in STAGES:
        for suffix in ("seconds", "calls", "peak_bytes"):
            field = stage + "_" + suffix
            row[field] = profile["metrics"].get(field, "NA")

    # A análise da geometria não entra no tempo nem na memória do algoritmo.
    feature_start = perf_counter()
    row.update(dict.fromkeys(FEATURE_FIELDS, "NA"))
    if points is not None and distances is not None:
        if geometry_points is None:
            geometry_points = planar_points(points, row["weight_type"])
        row.update(instance_features(geometry_points, distances))
        if row["route"] != "NA" and route_cost(row["route"], distances) != row["best_cost"]:
            raise ValueError("O custo retornado não corresponde à rota.")
    row["feature_seconds"] = perf_counter() - feature_start
    for field in ("route", "initial_route", "expanded_by_depth", "pruned_by_depth"):
        if row[field] != "NA":
            row[field] = json.dumps(row[field])
    return {field: row[field] for field in RESULT_FIELDS}
