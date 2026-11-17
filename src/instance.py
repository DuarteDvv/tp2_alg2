"""Leitura de instâncias TSPLIB com distância EUC_2D, ATT ou GEO."""

from hashlib import sha256
from math import acos, ceil, cos, floor, hypot, isfinite, pi, sqrt
from pathlib import Path

from .routes import route_cost


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def read_instance(path):
    """Retorna nome, coordenadas na ordem do arquivo e tipo de distância."""
    headers = {}
    points = []
    reading_points = False

    with open(path, encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line == "EOF":
                break
            if line == "NODE_COORD_SECTION":
                reading_points = True
            elif reading_points and line:
                city_id, x_coordinate, y_coordinate = line.split()
                if int(city_id) != len(points) + 1:
                    raise ValueError("Os IDs das cidades devem estar em ordem, de 1 a N.")
                point = (float(x_coordinate), float(y_coordinate))
                if not all(isfinite(coordinate) for coordinate in point):
                    raise ValueError("As coordenadas devem ser finitas.")
                points.append(point)
            elif ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

    weight_type = headers.get("EDGE_WEIGHT_TYPE")
    if headers.get("TYPE", "TSP") != "TSP":
        raise ValueError("A instância deve ser um TSP simétrico.")
    if weight_type not in ("EUC_2D", "ATT", "GEO"):
        raise ValueError("A instância deve usar distâncias EUC_2D, ATT ou GEO.")
    if not points or len(points) != int(headers["DIMENSION"]):
        raise ValueError("Quantidade de coordenadas diferente da dimensão.")

    return headers["NAME"], points, weight_type


def geographic_coordinates(points):
    """Converte graus e minutos TSPLIB para latitude/longitude em radianos."""
    def radians(coordinate):
        degrees = int(coordinate)
        minutes = coordinate - degrees
        return 3.141592 * (degrees + 5 * minutes / 3) / 180

    return [(radians(latitude), radians(longitude)) for latitude, longitude in points]


def planar_points(points, weight_type):
    """Projeção equiretangular local para fecho e features; não calcula custos."""
    if weight_type != "GEO":
        return points
    coordinates = geographic_coordinates(points)
    reference_longitude = coordinates[0][1]
    coordinates = [(latitude, reference_longitude + (longitude - reference_longitude + pi) % (2 * pi) - pi)
                   for latitude, longitude in coordinates]
    center_latitude = sum(latitude for latitude, _ in coordinates) / len(coordinates)
    center_longitude = sum(longitude for _, longitude in coordinates) / len(coordinates)
    return [(6378.388 * (longitude - center_longitude) * cos(center_latitude),
             6378.388 * (latitude - center_latitude)) for latitude, longitude in coordinates]


def distance_matrix(points, weight_type="EUC_2D"):
    """Calcula distâncias com o arredondamento definido pela TSPLIB."""
    if weight_type not in ("EUC_2D", "ATT", "GEO"):
        raise ValueError("Tipo de distância não suportado.")
    number_of_cities = len(points)
    distances = [[0] * number_of_cities for _ in range(number_of_cities)]
    if weight_type == "GEO":
        points = geographic_coordinates(points)

    for current_city in range(number_of_cities):
        current_x, current_y = points[current_city]
        for next_city in range(current_city + 1, number_of_cities):
            next_x, next_y = points[next_city]
            difference_x = current_x - next_x
            difference_y = current_y - next_y
            if weight_type == "GEO":
                longitude_cosine = cos(current_y - next_y)
                latitude_difference_cosine = cos(current_x - next_x)
                latitude_sum_cosine = cos(current_x + next_x)
                angle_cosine = ((1 + longitude_cosine) * latitude_difference_cosine
                                - (1 - longitude_cosine) * latitude_sum_cosine) / 2
                distance = int(6378.388 * acos(max(-1, min(1, angle_cosine))) + 1)
            elif weight_type == "ATT":
                distance = ceil(sqrt((difference_x ** 2 + difference_y ** 2) / 10))
            else:
                distance = floor(hypot(difference_x, difference_y) + 0.5)
            distances[current_city][next_city] = distance
            distances[next_city][current_city] = distance

    return distances


def find_instance(name):
    """Aceita o caminho completo ou só o nome, com ou sem .tsp."""
    path = Path(name)
    if path.is_file():
        return path
    if path.parent != Path("."):
        raise ValueError(f"Arquivo não encontrado: {path}")
    filename = path.name if path.suffix == ".tsp" else path.name + ".tsp"
    instance_folder = Path(__file__).resolve().parents[1] / "instancias"
    matches = list(instance_folder.rglob(filename))
    if len(matches) != 1:
        raise ValueError(f"Instância não encontrada ou nome ambíguo: {name}")
    return matches[0]


def reference_cost(path, distances):
    """Calcula o custo da rota .opt.tour ao lado da instância, se existir."""
    tour_path = Path(path).with_suffix(".opt.tour")
    if not tour_path.exists():
        return "NA"
    text = tour_path.read_text()
    if "TOUR_SECTION" not in text:
        raise ValueError(f"Arquivo de rota inválido: {tour_path}")
    route = []
    for value in text.split("TOUR_SECTION", 1)[1].split():
        if value in ("-1", "EOF"):
            break
        route.append(int(value) - 1)
    return route_cost(route, distances)
