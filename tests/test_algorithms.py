"""Casos pequenos permitem conferir o ótimo por enumeração completa."""

from itertools import permutations
import json
from pathlib import Path
import random
import tempfile
import unittest

from src.approximations import minimum_matching
from src.branch_and_bound import branch_and_bound
from src.experiments import run_experiment
from src.heuristics import STRATEGIES, initial_route
from src.instance import distance_matrix
from src.mst import mst_cost
from src.routes import route_cost, validate_route


def brute_force(distances):
    return min(route_cost([0, *tail], distances)
               for tail in permutations(range(1, len(distances))))


class AlgorithmTests(unittest.TestCase):
    def check_all_strategies(self, points):
        distances = distance_matrix(points)
        optimum = brute_force(distances)
        for strategy in STRATEGIES:
            with self.subTest(strategy=strategy, points=points):
                route = initial_route(strategy, distances, points)
                validate_route(route, len(points))
                result = branch_and_bound(distances, route, time_limit=5)
                self.assertEqual(result.status, "optimal")
                self.assertEqual(result.best_cost, optimum)
                self.assertEqual(route_cost(result.route, distances), optimum)
                self.assertLessEqual(result.best_cost, result.initial_cost)

    def test_all_starts_against_brute_force(self):
        generator = random.Random(42)
        for size in range(3, 9):
            for _ in range(3):
                points = [(generator.randrange(30), generator.randrange(30)) for _ in range(size)]
                self.check_all_strategies(points)

    def test_degenerate_instances(self):
        for points in (
            [(0, 0)], [(0, 0), (3, 4)], [(1, 1)] * 5,
            [(0, 0), (1, 0), (2, 0), (3, 0), (1, 0)],
        ):
            self.check_all_strategies(points)

    def test_nonmetric_symmetric_matrix(self):
        # O limite inferior também deve valer sem desigualdade triangular.
        generator = random.Random(7)
        for size in range(3, 8):
            distances = [[0] * size for _ in range(size)]
            for i in range(size):
                for j in range(i):
                    distances[i][j] = distances[j][i] = generator.randrange(50)
            result = branch_and_bound(distances, list(range(size)), 5)
            self.assertEqual(result.status, "optimal")
            self.assertEqual(result.best_cost, brute_force(distances))

    def test_timeout_preserves_incumbent(self):
        distances = distance_matrix([(0, 0), (3, 0), (3, 4), (0, 4)])
        route = [0, 2, 1, 3]
        result = branch_and_bound(distances, route, 0)
        self.assertEqual(result.status, "timeout")
        self.assertEqual(result.route, route)
        self.assertEqual(result.best_cost, route_cost(route, distances))

    def test_root_pruning_and_input_unchanged(self):
        distances = distance_matrix([(0, 0), (3, 0), (3, 4), (0, 4)])
        route = [0, 1, 2, 3]
        result = branch_and_bound(distances, route)
        self.assertEqual(route, [0, 1, 2, 3])
        self.assertEqual(result.best_cost, 14)
        self.assertGreater(result.nodes_pruned, 0)

    def test_mst_and_matching(self):
        distances = distance_matrix([(0, 0), (3, 0), (3, 4), (0, 4)])
        self.assertEqual(mst_cost(distances, [0, 1, 2, 3]), 10)
        matching = minimum_matching(distances, [0, 1, 2, 3])
        self.assertEqual(sum(distances[a][b] for a, b in matching), 6)

    def test_metric_approximation_bounds(self):
        # Distâncias inteiras entre pontos colineares são métricas exatas.
        points = [(x, 0) for x in (0, 2, 7, 8, 12, 20)]
        distances = distance_matrix(points)
        optimum = brute_force(distances)
        for strategy, factor in (("twice", 2), ("christofides", 1.5)):
            cost = route_cost(initial_route(strategy, distances, points), distances)
            self.assertLessEqual(cost, factor * optimum)

    def test_invalid_inputs(self):
        for distances in ([], [[0, 1]], [[0, 2], [1, 0]], [[0, -1], [-1, 0]]):
            with self.assertRaises(ValueError):
                branch_and_bound(distances, [0])
        with self.assertRaises(ValueError):
            branch_and_bound([[0, 1], [1, 0]], [0, 0])

    def test_experiment_output_and_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "square.tsp"
            path.write_text(
                "NAME: square\nDIMENSION: 4\nEDGE_WEIGHT_TYPE: EUC_2D\n"
                "NODE_COORD_SECTION\n1 0 0\n2 3 0\n3 3 4\n4 0 4\nEOF\n"
            )
            for strategy in STRATEGIES:
                row = run_experiment(path, strategy, memory=True)
                self.assertEqual(row["optimal_cost"], 14)
                self.assertEqual(row["status"], "optimal")
                self.assertGreater(row["peak_bytes"], 0)
                validate_route(json.loads(row["route"]), 4)
            row = run_experiment(path, "trivial", time_limit=1e-12)
            self.assertEqual(row["status"], "timeout")
            self.assertEqual(row["optimal_cost"], "NA")
            row = run_experiment(path, "christofides", initial_only=True)
            self.assertEqual(row["status"], "heuristic")
            self.assertEqual(row["optimal_cost"], "NA")


if __name__ == "__main__":
    unittest.main()
