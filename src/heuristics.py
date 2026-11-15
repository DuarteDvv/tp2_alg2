"""Heurísticas para construir as rotas iniciais."""

from .approximations import christofides, twice_around_tree
from .convex_hull import hull_insertion
from .profiling import Profiler


STRATEGIES = ("trivial", "nearest", "hull", "twice", "christofides")


def trivial_route(distances):
    return list(range(len(distances)))


def nearest_neighbor(distances):
    """Começa na cidade 0 e escolhe a cidade não visitada mais próxima."""
    route = [0]
    remaining = set(range(1, len(distances)))

    while remaining:
        current = route[-1]
        next_city = min(remaining, key=lambda city: (distances[current][city], city))
        route.append(next_city)
        remaining.remove(next_city)

    return route


def initial_route(strategy, distances, points, profile=None):
    profile = profile if profile is not None else Profiler()
    if strategy == "trivial":
        return trivial_route(distances)
    if strategy == "nearest":
        return nearest_neighbor(distances)
    if strategy == "hull":
        return hull_insertion(distances, points, profile)
    if strategy == "twice":
        return twice_around_tree(distances, profile)
    if strategy == "christofides":
        return christofides(distances, profile)
    raise ValueError(f"Estratégia desconhecida: {strategy}")
