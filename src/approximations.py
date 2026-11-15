"""Twice-around-the-tree e Christofides."""

import networkx as nx

from .mst import mst_edges


def euler_shortcut(size, edges):
    """Hierholzer em multigrafo, seguido da remoção de visitas repetidas."""
    adjacency = [[] for _ in range(size)]
    for edge_id, (a, b) in enumerate(edges):
        adjacency[a].append((b, edge_id))
        adjacency[b].append((a, edge_id))

    used = set()
    stack = [0]
    circuit = []
    while stack:
        city = stack[-1]
        while adjacency[city] and adjacency[city][-1][1] in used:
            adjacency[city].pop()
        if adjacency[city]:
            neighbor, edge_id = adjacency[city].pop()
            used.add(edge_id)
            stack.append(neighbor)
        else:
            circuit.append(stack.pop())

    return list(dict.fromkeys(reversed(circuit)))


def minimum_matching(distances, odd_vertices):
    graph = nx.Graph()
    graph.add_nodes_from(odd_vertices)
    for index, a in enumerate(odd_vertices):
        for b in odd_vertices[index + 1:]:
            graph.add_edge(a, b, weight=distances[a][b])
    matching = nx.min_weight_matching(graph, weight="weight")
    if len(matching) * 2 != len(odd_vertices):
        raise ValueError("O emparelhamento não cobriu todos os vértices ímpares.")
    return sorted((min(a, b), max(a, b)) for a, b in matching)


def twice_around_tree(distances, profile):
    tree = profile.measure("mst", mst_edges, distances, list(range(len(distances))))
    return profile.measure("euler", euler_shortcut, len(distances), tree + tree)


def christofides(distances, profile):
    size = len(distances)
    tree = profile.measure("mst", mst_edges, distances, list(range(size)))
    degrees = [0] * size
    for a, b in tree:
        degrees[a] += 1
        degrees[b] += 1
    odd = [city for city in range(size) if degrees[city] % 2]
    matching = profile.measure("matching", minimum_matching, distances, odd)
    return profile.measure("euler", euler_shortcut, size, tree + matching)
