"""características geométricas e topológicas usadas na análise."""

from collections import Counter
from itertools import combinations
from math import hypot, log
from statistics import mean, pstdev

from .convex_hull import convex_hull
from .mst import mst_edges

FEATURE_FIELDS = (
    "bounding_box_width", "bounding_box_height", "aspect_ratio", "hull_fraction",
    "spatial_entropy", "mst_max_degree", "mst_odd_vertices", "mst_cost", "nearest_neighbor_cv",
    "triangle_violations", "maximum_triangle_violation",
)


def instance_features(points, distances):
    number_of_cities = len(points)
    x_coordinates = [point[0] for point in points]
    y_coordinates = [point[1] for point in points]
    minimum_x, maximum_x = min(x_coordinates), max(x_coordinates)
    minimum_y, maximum_y = min(y_coordinates), max(y_coordinates)
    width = maximum_x - minimum_x
    height = maximum_y - minimum_y
    shortest_side = min(width, height)
    aspect_ratio = max(width, height) / shortest_side if shortest_side else "NA"
    if width == height == 0:

        aspect_ratio = 1

    # entropia em uma grade fixa 4x4 sobre o bounding box de cada instância.

    cells = Counter()
    for x_coordinate, y_coordinate in points:

        column = min(3, int(4 * (x_coordinate - minimum_x) / width)) if width else 0
        row = min(3, int(4 * (y_coordinate - minimum_y) / height)) if height else 0
        cells[column, row] += 1

    spatial_entropy = -sum((count / number_of_cities) * log(count / number_of_cities)
                           for count in cells.values())

    tree = mst_edges(distances, range(number_of_cities))
    degrees = [0] * number_of_cities
    for first_city, second_city in tree:

        degrees[first_city] += 1
        degrees[second_city] += 1

    # distâncias euclidianas sem arredondamento descrevem a geometria.

    nearest_distances = []
    if number_of_cities > 1:

        for city, (x_coordinate, y_coordinate) in enumerate(points):

            nearest_distances.append(min(
                hypot(x_coordinate - other_x, y_coordinate - other_y)
                for other_city, (other_x, other_y) in enumerate(points) if other_city != city
            ))

    nearest_mean = mean(nearest_distances) if nearest_distances else 0
    nearest_cv = pstdev(nearest_distances) / nearest_mean if nearest_mean else 0

    triangle_violations = 0
    maximum_violation = 0
    for first_city, second_city, third_city in combinations(range(number_of_cities), 3):

        sides = (distances[first_city][second_city], distances[first_city][third_city],
                 distances[second_city][third_city])
        excess = 2 * max(sides) - sum(sides)
        if excess > 0:

            triangle_violations += 1
            maximum_violation = max(maximum_violation, excess)

    return {
        "bounding_box_width": width,
        "bounding_box_height": height,
        "aspect_ratio": aspect_ratio,
        "hull_fraction": len(convex_hull(points)) / number_of_cities,
        "spatial_entropy": spatial_entropy,
        "mst_max_degree": max(degrees),
        "mst_odd_vertices": sum(degree % 2 for degree in degrees),
        "mst_cost": sum(distances[first][second] for first, second in tree),
        "nearest_neighbor_cv": nearest_cv,
        "triangle_violations": triangle_violations,
        "maximum_triangle_violation": maximum_violation,
    }
