"""Rotas usam índices de 0 a N-1, sem repetir a cidade inicial no final."""


def validate_route(route, size):
    if len(route) != size or set(route) != set(range(size)):
        raise ValueError("A rota deve visitar cada cidade exatamente uma vez.")


def route_cost(route, distances):
    """Inclui a distância de retorno à primeira cidade."""
    validate_route(route, len(distances))
    return sum(distances[route[i - 1]][route[i]] for i in range(len(route)))
