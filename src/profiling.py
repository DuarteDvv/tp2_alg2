"""Medição das etapas de inicialização; memória é opcional."""

from time import perf_counter
import tracemalloc


class Profiler:
    def __init__(self, memory=False):
        self.memory = memory
        self.metrics = {}
        self.peak_bytes = 0

    def measure(self, name, function, *args):
        if self.memory:
            self.peak_bytes = max(self.peak_bytes, tracemalloc.get_traced_memory()[1])
            before = tracemalloc.get_traced_memory()[0]
            tracemalloc.reset_peak()
        start = perf_counter()
        value = function(*args)
        self.metrics[name + "_seconds"] = perf_counter() - start
        if self.memory:
            current, peak = tracemalloc.get_traced_memory()
            self.metrics[name + "_peak_bytes"] = max(0, peak - before)
            self.peak_bytes = max(self.peak_bytes, peak)
        return value
