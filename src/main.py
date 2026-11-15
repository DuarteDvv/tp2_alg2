"""Execução de uma instância pela linha de comando."""

import argparse
import json

from .experiments import run_experiment, time_limit_arg
from .heuristics import STRATEGIES


def main():
    parser = argparse.ArgumentParser(description="Resolve TSP com Branch-and-Bound.")
    parser.add_argument("instance", help="Caminho do arquivo .tsp (EUC_2D)")
    parser.add_argument("--strategy", choices=STRATEGIES, default="nearest")
    parser.add_argument("--time-limit", type=time_limit_arg, default=1800)
    parser.add_argument("--memory", action="store_true")
    parser.add_argument("--initial-only", action="store_true")
    args = parser.parse_args()

    result = run_experiment(args.instance, args.strategy, args.time_limit,
                            args.memory, args.initial_only)
    print(f"Instância: {result['instance']} | Cidades: {result['size']}")
    print(f"Inicialização: {result['strategy']} | Custo inicial: {result['initial_cost']}")
    print(f"Status: {result['status']} | Melhor custo: {result['best_cost']}")
    print(f"Ótimo comprovado: {result['optimal_cost']}")
    print(f"Tempo total: {result['total_seconds']:.6f} s")
    print(f"Nós expandidos: {result['nodes_expanded']} | Podados: {result['nodes_pruned']}")
    route = json.loads(result["route"])
    print("Rota (posição no arquivo, a partir de 1):")
    print(" -> ".join(str(city + 1) for city in route + [route[0]]))


if __name__ == "__main__":
    main()
