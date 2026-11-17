"""CSV incremental e cálculo de gaps usando ótimos comprovados."""

import argparse
import csv
from pathlib import Path

from .runner import gap_percent


def prepare_csv(path, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size:
        with path.open(newline="", encoding="utf-8") as file:
            if next(csv.reader(file)) != list(fields):
                raise ValueError("CSV de outra versão: escolha outro arquivo de saída.")
    else:
        with path.open("w", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow(fields)


def append_result(path, result):
    with Path(path).open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(result))
        writer.writerow(result)
        file.flush()


def save_gaps(path):
    """Compartilha o ótimo entre execuções da mesma instância (hash idêntico).

    Não usa a melhor rota parcial como se fosse o ótimo.
    Atualiza as referências e os gaps no próprio CSV.
    """
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    references = {}
    for row in rows:
        if row["reference_cost"] == "NA":
            continue
        instance_hash = row["instance_sha256"]
        reference = float(row["reference_cost"])
        if instance_hash in references and references[instance_hash][0] != reference:
            raise ValueError("Ótimos conflitantes para o mesmo arquivo de instância.")
        references[instance_hash] = (reference, row["reference_source"])
    for row in rows:
        reference = references.get(row["instance_sha256"])
        if reference is None:
            continue
        optimum, source = reference
        row["reference_cost"], row["reference_source"] = optimum, source
        for cost_field, gap_field in (("initial_cost", "initial_gap_percent"),
                                      ("best_cost", "best_gap_percent")):
            cost = float(row[cost_field]) if row[cost_field] != "NA" else "NA"
            row[gap_field] = gap_percent(cost, optimum)
    if rows:
        temporary_path = path.with_suffix(".tmp")
        with temporary_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        temporary_path.replace(path)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consolida gaps de um CSV já coletado.")
    parser.add_argument("csv", type=Path)
    print(save_gaps(parser.parse_args().csv))
