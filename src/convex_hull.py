"""fecho convexo e inserção gulosa dos pontos restantes."""

from .profiling import measure


def convex_hull(points):
    def orientation(first_city, second_city, third_city):
        first_x, first_y = points[first_city]
        second_x, second_y = points[second_city]
        third_x, third_y = points[third_city]
        return ((second_x - first_x) * (third_y - first_y)
                - (second_y - first_y) * (third_x - first_x))

    ordered_cities = sorted(range(len(points)), key=lambda city: (*points[city], city))
    # pontos duplicados entram depois pela inserção.

    unique_cities = []
    for city in ordered_cities:

        if not unique_cities or points[city] != points[unique_cities[-1]]:

            unique_cities.append(city)

    if len(unique_cities) <= 1:

        return unique_cities

    def build_half(cities):
        hull = []
        for city in cities:

            while len(hull) >= 2 and orientation(hull[-2], hull[-1], city) <= 0:

                hull.pop()

            hull.append(city)

        return hull

    lower_half = build_half(unique_cities)
    upper_half = build_half(reversed(unique_cities))
    return lower_half[:-1] + upper_half[:-1]


def insert_remaining(distances, hull):
    route = hull.copy()
    remaining_cities = set(range(len(distances))) - set(route)
    while remaining_cities:

        best_insertion = None
        for city in remaining_cities:

            for position, previous_city in enumerate(route):

                next_city = route[(position + 1) % len(route)]
                extra_cost = (distances[previous_city][city] + distances[city][next_city]
                              - distances[previous_city][next_city])
                candidate = (extra_cost, city, position)
                if best_insertion is None or candidate < best_insertion:

                    best_insertion = candidate

        _, city, position = best_insertion
        route.insert(position + 1, city)
        remaining_cities.remove(city)

    return route


def hull_insertion(distances, points, profile):
    hull = measure(profile, "hull", convex_hull, points)
    return measure(profile, "insertion", insert_remaining, distances, hull)
