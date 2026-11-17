"""Árvore geradora mínima pelo algoritmo de Prim, em O(N²)."""


def mst_edges(distances, vertices, check_time=None):
    unvisited_cities = set(vertices)
    if len(unvisited_cities) < 2:
        return []

    first_city = min(unvisited_cities)
    unvisited_cities.remove(first_city)
    cheapest_distance = {city: distances[first_city][city] for city in unvisited_cities}
    parent_city = {city: first_city for city in unvisited_cities}
    tree_edges = []

    while unvisited_cities:
        if check_time is not None:
            check_time()
        next_city = min(unvisited_cities, key=lambda city: (cheapest_distance[city], city))
        tree_edges.append((parent_city[next_city], next_city))
        unvisited_cities.remove(next_city)
        for city in unvisited_cities:
            if distances[next_city][city] < cheapest_distance[city]:
                cheapest_distance[city] = distances[next_city][city]
                parent_city[city] = next_city

    return tree_edges


def mst_cost(distances, vertices, check_time=None):
    tree_edges = mst_edges(distances, vertices, check_time)
    return sum(distances[first_city][second_city] for first_city, second_city in tree_edges)
