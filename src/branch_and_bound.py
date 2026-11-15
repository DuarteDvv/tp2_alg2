"""Busca exata em profundidade com limite inferior baseado em MST."""

from dataclasses import dataclass
from math import isfinite
from time import perf_counter

from .mst import mst_cost
from .routes import route_cost


@dataclass
class SearchResult:
    status: str
    route: list
    best_cost: float
    initial_cost: float
    search_seconds: float
    bound_seconds: float
    bound_calls: int
    nodes_expanded: int
    nodes_pruned: int
    complete_routes: int
    max_depth: int


def branch_and_bound(distances, initial_route, time_limit=1800):
    """Retorna a melhor rota; só status 'optimal' comprova otimalidade.

    Requer matriz simétrica, finita e não negativa. A cidade inicial é 0.
    O limite de tempo cobre a busca e sua preparação, mas não a construção
    da rota inicial, que deve ser medida pelo chamador.
    """
    if not isfinite(time_limit) or time_limit < 0:
        raise ValueError("O limite de tempo deve ser finito e não negativo.")

    start = perf_counter()
    deadline = start + time_limit
    size = len(distances)
    if size == 0 or any(len(row) != size for row in distances):
        raise ValueError("A matriz deve ser quadrada e não vazia.")
    for i in range(size):
        for j in range(size):
            value = distances[i][j]
            if not isfinite(value) or value < 0 or value != distances[j][i]:
                raise ValueError("As distâncias devem ser finitas, não negativas e simétricas.")
        if distances[i][i] != 0:
            raise ValueError("A diagonal da matriz deve ser zero.")

    initial_cost = route_cost(initial_route, distances)
    result = SearchResult(
        status="optimal", route=list(initial_route), best_cost=initial_cost,
        initial_cost=initial_cost, search_seconds=0, bound_seconds=0,
        bound_calls=0, nodes_expanded=0, nodes_pruned=0,
        complete_routes=0, max_depth=0,
    )
    path = [0]

    def check_time():
        if perf_counter() >= deadline:
            raise TimeoutError

    def lower_bound(current, remaining):
        # Toda conclusão da rota conecta a ponta e a origem aos vértices
        # restantes, cujas arestas internas custam pelo menos uma MST.
        bound_start = perf_counter()
        result.bound_calls += 1
        try:
            tree = mst_cost(distances, remaining, check_time)
            return (tree
                    + min(distances[current][city] for city in remaining)
                    + min(distances[0][city] for city in remaining))
        finally:
            result.bound_seconds += perf_counter() - bound_start

    def search(current, remaining, cost):
        check_time()
        result.max_depth = max(result.max_depth, len(path) - 1)
        if not remaining:
            result.complete_routes += 1
            total = cost + distances[current][0]
            if total < result.best_cost:
                result.best_cost = total
                result.route = path.copy()
            return

        if cost >= result.best_cost or cost + lower_bound(current, remaining) >= result.best_cost:
            result.nodes_pruned += 1
            return

        result.nodes_expanded += 1
        # Visitar primeiro as cidades próximas tende a melhorar cedo a rota.
        candidates = sorted(remaining, key=lambda city: (distances[current][city], city))
        for city in candidates:
            path.append(city)
            search(city, [other for other in remaining if other != city],
                   cost + distances[current][city])
            path.pop()

    try:
        check_time()
        search(0, list(range(1, size)), 0)
        check_time()
    except TimeoutError:
        result.status = "timeout"

    result.search_seconds = perf_counter() - start
    return result
