"""busca exata em profundidade com limite inferior baseado em MST."""

from math import isfinite
from time import perf_counter

from .mst import mst_cost
from .profiling import create_profile, measure
from .routes import route_cost


def validate_distances(distances):
    number_of_cities = len(distances)
    if not number_of_cities or any(len(row) != number_of_cities for row in distances):

        raise ValueError("A matriz deve ser quadrada e não vazia.")

    for city in range(number_of_cities):

        if distances[city][city] != 0:

            raise ValueError("A diagonal da matriz deve ser zero.")

        for other_city in range(number_of_cities):

            distance = distances[city][other_city]
            if not isfinite(distance) or distance < 0 or distance != distances[other_city][city]:

                raise ValueError("As distâncias devem ser finitas, não negativas e simétricas.")


def branch_and_bound(distances, initial_route, time_limit=1800, profile=None):
    """retorna um dicionário. Apenas status 'optimal' comprova o ótimo.

    o tempo desta função não inclui a construção da rota inicial.
    não requer desigualdade triangular.
    """

    if time_limit is not None and (not isfinite(time_limit) or time_limit < 0):

        raise ValueError("O limite de tempo deve ser finito e não negativo.")

    start_time = perf_counter()
    deadline = start_time + time_limit if time_limit is not None else None
    validate_distances(distances)
    number_of_cities = len(distances)
    initial_cost = route_cost(initial_route, distances)
    if profile is None:

        profile = create_profile()

    result = {
        "status": "optimal", "route": list(initial_route),
        "best_cost": initial_cost, "initial_cost": initial_cost,
        "search_seconds": 0, "bound_seconds": 0, "bound_calls": 0,
        "nodes_visited": 0, "nodes_expanded": 0, "nodes_pruned": 0, "nodes_interrupted": 0,
        "complete_routes": 0, "max_depth": 0,
        "expanded_by_depth": [0] * number_of_cities,
        "pruned_by_depth": [0] * number_of_cities,
    }
    # a ordem é calculada uma vez, em vez de ordenar a cada estado.

    neighbors = [sorted(range(number_of_cities), key=lambda other: (row[other], other))
                 for row in distances]
    path = [0]
    unvisited_cities = set(range(1, number_of_cities))

    def check_time():
        if deadline is not None and perf_counter() >= deadline:

            raise TimeoutError

    def lower_bound(current_city):
        bound_start = perf_counter()
        result["bound_calls"] += 1
        try:
            tree_cost = measure(profile, "search_mst", mst_cost,
                                distances, unvisited_cities, check_time)
            departure_cost = min(distances[current_city][city] for city in unvisited_cities)
            return_cost = min(distances[0][city] for city in unvisited_cities)
            return tree_cost + departure_cost + return_cost
        finally:
            result["bound_seconds"] += perf_counter() - bound_start

    def search(current_city, path_cost):
        check_time()
        depth = len(path) - 1
        result["nodes_visited"] += 1
        result["max_depth"] = max(result["max_depth"], depth)
        if not unvisited_cities:

            result["complete_routes"] += 1
            complete_cost = path_cost + distances[current_city][0]
            if complete_cost < result["best_cost"]:

                result["best_cost"] = complete_cost
                result["route"] = path.copy()

            return

        if (path_cost >= result["best_cost"]
                or path_cost + lower_bound(current_city) >= result["best_cost"]):

            result["nodes_pruned"] += 1
            result["pruned_by_depth"][depth] += 1
            return

        result["nodes_expanded"] += 1
        result["expanded_by_depth"][depth] += 1
        for next_city in neighbors[current_city]:

            if next_city not in unvisited_cities:

                continue

            path.append(next_city)
            unvisited_cities.remove(next_city)
            try:
                search(next_city, path_cost + distances[current_city][next_city])
            finally:
                unvisited_cities.add(next_city)
                path.pop()

    try:
        search(0, 0)
    except TimeoutError:
        result["status"] = "timeout"
        result["nodes_interrupted"] = (result["nodes_visited"] - result["nodes_expanded"]
                                       - result["nodes_pruned"] - result["complete_routes"])
    result["search_seconds"] = perf_counter() - start_time
    return result
