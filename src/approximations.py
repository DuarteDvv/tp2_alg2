"""Twice-around-the-tree e Christofides."""

import networkx as nx

from .mst import mst_edges
from .profiling import measure


def euler_shortcut(number_of_cities, edges):
    """Percorre todas as arestas com Hierholzer e elimina visitas repetidas."""
    adjacency = [[] for _ in range(number_of_cities)]
    for edge_id, (first_city, second_city) in enumerate(edges):
        adjacency[first_city].append((second_city, edge_id))
        adjacency[second_city].append((first_city, edge_id))

    used_edges = [False] * len(edges)
    stack = [0]
    circuit = []
    while stack:
        current_city = stack[-1]
        while adjacency[current_city] and used_edges[adjacency[current_city][-1][1]]:
            adjacency[current_city].pop()
        if adjacency[current_city]:
            next_city, edge_id = adjacency[current_city].pop()
            used_edges[edge_id] = True
            stack.append(next_city)
        else:
            circuit.append(stack.pop())

    route = []
    visited_cities = set()
    for city in reversed(circuit):
        if city not in visited_cities:
            route.append(city)
            visited_cities.add(city)
    return route


def minimum_matching(distances, odd_vertices):
    graph = nx.Graph()
    graph.add_nodes_from(odd_vertices)
    for index, first_city in enumerate(odd_vertices):
        for second_city in odd_vertices[index + 1:]:
            graph.add_edge(first_city, second_city, weight=distances[first_city][second_city])
    matching = nx.min_weight_matching(graph, weight="weight")
    if len(matching) * 2 != len(odd_vertices):
        raise ValueError("O emparelhamento não cobriu todos os vértices ímpares.")
    return sorted((min(first, second), max(first, second)) for first, second in matching)


def twice_around_tree(distances, profile):
    number_of_cities = len(distances)
    tree_edges = measure(profile, "mst", mst_edges, distances, range(number_of_cities))
    return measure(profile, "euler", euler_shortcut, number_of_cities, tree_edges + tree_edges)


def christofides(distances, profile):
    number_of_cities = len(distances)
    tree_edges = measure(profile, "mst", mst_edges, distances, range(number_of_cities))
    degrees = [0] * number_of_cities
    for first_city, second_city in tree_edges:
        degrees[first_city] += 1
        degrees[second_city] += 1
    odd_vertices = [city for city in range(number_of_cities) if degrees[city] % 2]
    matching = measure(profile, "matching", minimum_matching, distances, odd_vertices)
    return measure(profile, "euler", euler_shortcut, number_of_cities, tree_edges + matching)
