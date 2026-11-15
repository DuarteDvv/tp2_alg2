"""Árvore geradora mínima pelo algoritmo de Prim, em O(N²)."""


def mst_edges(distances, vertices, check_time=None):
    """Arestas da árvore no subconjunto de vértices informado."""
    if len(vertices) < 2:
        return []

    remaining = set(vertices)
    first = vertices[0]
    remaining.remove(first)
    cheapest = {city: distances[first][city] for city in remaining}
    parent = {city: first for city in remaining}
    edges = []

    while remaining:
        if check_time is not None:
            check_time()
        city = min(remaining, key=lambda city: (cheapest[city], city))
        edges.append((parent[city], city))
        remaining.remove(city)
        for other in remaining:
            if distances[city][other] < cheapest[other]:
                cheapest[other] = distances[city][other]
                parent[other] = city

    return edges


def mst_cost(distances, vertices, check_time=None):
    return sum(distances[i][j] for i, j in mst_edges(distances, vertices, check_time))
