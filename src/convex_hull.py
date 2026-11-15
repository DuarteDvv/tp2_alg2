"""Fecho convexo e inserção gulosa dos pontos restantes."""


def convex_hull(points):
    def cross(a, b, c):
        ax, ay = points[a]
        bx, by = points[b]
        cx, cy = points[c]
        return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)

    ordered = sorted(range(len(points)), key=lambda city: (*points[city], city))
    # Coordenadas repetidas entram depois pela inserção.
    unique = []
    for city in ordered:
        if not unique or points[city] != points[unique[-1]]:
            unique.append(city)
    if len(unique) <= 1:
        return unique

    def half(vertices):
        hull = []
        for city in vertices:
            while len(hull) >= 2 and cross(hull[-2], hull[-1], city) <= 0:
                hull.pop()
            hull.append(city)
        return hull

    return half(unique)[:-1] + half(reversed(unique))[:-1]


def insert_remaining(distances, hull):
    route = hull.copy()
    remaining = set(range(len(distances))) - set(route)
    while remaining:
        choices = (
            (distances[a][city] + distances[city][route[(i + 1) % len(route)]]
             - distances[a][route[(i + 1) % len(route)]], city, i)
            for city in remaining for i, a in enumerate(route)
        )
        _, city, position = min(choices)
        route.insert(position + 1, city)
        remaining.remove(city)
    return route


def hull_insertion(distances, points, profile):
    hull = profile.measure("hull", convex_hull, points)
    return profile.measure("insertion", insert_remaining, distances, hull)
