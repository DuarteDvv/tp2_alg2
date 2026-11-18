"""rotas usam índices de 0 a N-1, sem repetir a cidade inicial no final."""


def validate_route(route, number_of_cities):
    if len(route) != number_of_cities or set(route) != set(range(number_of_cities)):

        raise ValueError("A rota deve visitar cada cidade exatamente uma vez.")


def route_cost(route, distances):
    """inclui a distância de retorno à primeira cidade."""

    validate_route(route, len(distances))
    total_cost = 0
    for position, current_city in enumerate(route):

        previous_city = route[position - 1]
        total_cost += distances[previous_city][current_city]

    return total_cost
