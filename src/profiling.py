"""tempos acumulados e picos adicionais de alocações Python por etapa."""

from time import perf_counter
import tracemalloc


STAGES = ("read", "matrix", "hull", "insertion", "mst", "matching", "euler", "search_mst")


def create_profile(memory=False):
    return {"memory": memory, "metrics": {}, "peak_bytes": 0}


def subroutine_peak(metrics):
    """maior pico adicional entre as subrotinas, excluindo a leitura."""

    peaks = []
    for stage in STAGES:

        if stage == "read":

            continue

        value = metrics.get(stage + "_peak_bytes", "NA")
        if value != "NA":

            peaks.append(int(value))

    return max(peaks) if peaks else "NA"


def measure(profile, stage, function, *arguments):
    metrics = profile["metrics"]
    metrics[stage + "_calls"] = metrics.get(stage + "_calls", 0) + 1
    if profile["memory"]:

        current_bytes, peak_bytes = tracemalloc.get_traced_memory()
        profile["peak_bytes"] = max(profile["peak_bytes"], peak_bytes)
        tracemalloc.reset_peak()

    start_time = perf_counter()
    try:
        return function(*arguments)
    finally:
        elapsed_seconds = perf_counter() - start_time
        metrics[stage + "_seconds"] = metrics.get(stage + "_seconds", 0) + elapsed_seconds
        if profile["memory"]:

            _, peak_bytes = tracemalloc.get_traced_memory()
            key = stage + "_peak_bytes"
            metrics[key] = max(metrics.get(key, 0), peak_bytes - current_bytes)
            profile["peak_bytes"] = max(profile["peak_bytes"], peak_bytes)
