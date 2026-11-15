"""Leitura de instâncias TSPLIB com distância EUC_2D."""

from math import floor, hypot


def read_instance(path):
    """Retorna o nome e as coordenadas, na ordem do arquivo."""
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
                _, x, y = line.split()
                points.append((float(x), float(y)))
            elif ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

    if headers.get("EDGE_WEIGHT_TYPE") != "EUC_2D":
        raise ValueError("A instância deve usar distâncias EUC_2D.")
    if not points or len(points) != int(headers["DIMENSION"]):
        raise ValueError("Quantidade de coordenadas diferente da dimensão.")

    return headers["NAME"], points


def distance_matrix(points):
    """Calcula distâncias com o arredondamento definido pela TSPLIB."""
    size = len(points)
    distances = [[0] * size for _ in range(size)]

    for i in range(size):
        x1, y1 = points[i]
        for j in range(i + 1, size):
            x2, y2 = points[j]
            distance = floor(hypot(x1 - x2, y1 - y2) + 0.5)
            distances[i][j] = distance
            distances[j][i] = distance

    return distances
