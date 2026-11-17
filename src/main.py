"""Executa e salva um experimento por comando."""

import argparse
from pathlib import Path

from .heuristics import STRATEGIES
from .instance import find_instance
from .results import append_result, prepare_csv
from .runner import RESULT_FIELDS, run_experiment
from .timeout import time_limit_arg


def main():
    parser = argparse.ArgumentParser(description="Executa um experimento de TSP e salva em CSV.")
    parser.add_argument("instance", help="Nome da instância ou caminho do arquivo .tsp")
    parser.add_argument("--strategy", choices=STRATEGIES, default="trivial")
    time_options = parser.add_mutually_exclusive_group()
    time_options.add_argument("--time-limit", type=time_limit_arg, default=1800, help="Limite em segundos")
    time_options.add_argument("--no-time-limit", action="store_true", help="Busca sem limite para comprovar o ótimo")
    parser.add_argument("--memory", action="store_true", help="Mede memória em uma rodada separada")
    parser.add_argument("--initial-only", action="store_true", help="Executa só a heurística inicial")
    parser.add_argument("--output", type=Path, help="CSV de saída; por padrão, results/tempos.csv ou memoria.csv")
    arguments = parser.parse_args()

    try:
        instance_path = find_instance(arguments.instance)
        output_path = arguments.output or Path("results/memoria.csv" if arguments.memory else "results/tempos.csv")
        prepare_csv(output_path, RESULT_FIELDS)
        time_limit = None if arguments.no_time_limit else arguments.time_limit
        limit_description = "sem limite" if time_limit is None else f"limite {time_limit:g} s"
        print(f"Executando {instance_path.stem} | {arguments.strategy} | {limit_description}", flush=True)
        result = run_experiment(instance_path, arguments.strategy, time_limit,
                                arguments.memory, arguments.initial_only)
        append_result(output_path, result)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Erro: {error}\n")

    print(f"Status: {result['status']}")
    print(f"Custo inicial: {result['initial_cost']} | Melhor custo: {result['best_cost']}")
    print(f"Referência ótima: {result['reference_cost']}")
    print(f"Tempo: {result['total_seconds']:.3f} s")
    print(f"Nós expandidos: {result['nodes_expanded']} | Podados: {result['nodes_pruned']}")
    print(f"Resultado salvo em: {output_path}")


if __name__ == "__main__":
    main()
