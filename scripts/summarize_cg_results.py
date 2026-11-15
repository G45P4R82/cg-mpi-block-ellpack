#!/usr/bin/env python3
import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path


input_path = Path(sys.argv[1] if len(sys.argv) > 1 else "results/processed/cg_results_tvbox.csv")
output_path = Path(sys.argv[2] if len(sys.argv) > 2 else "results/processed/cg_stats_tvbox.csv")

with input_path.open(newline="") as stream:
    rows = list(csv.DictReader(stream))

groups = defaultdict(list)
for row in rows:
    key = (
        row["family"],
        row["matrix"],
        row["block_size"],
        row["mpi_processes"],
        row["omp_threads"],
    )
    groups[key].append(row)

output_path.parent.mkdir(parents=True, exist_ok=True)
fields = [
    "family", "matrix", "block_size", "mpi_processes", "omp_threads", "repetitions",
    "solve_mean_s", "solve_min_s", "solve_max_s", "solve_stddev_s",
    "iterations_mean", "relative_residual_max", "solution_error_mean", "padding_overhead",
]
with output_path.open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for key in sorted(groups):
        family, matrix, block, mpi, threads = key
        values = groups[key]
        solve = [float(row["solve_time_s"]) for row in values]
        iterations = [float(row["iterations"]) for row in values]
        residual = [float(row["relative_residual"]) for row in values]
        errors = [float(row["solution_error"]) for row in values]
        padding = [float(row["padding_overhead"]) for row in values]
        writer.writerow({
            "family": family,
            "matrix": matrix,
            "block_size": block,
            "mpi_processes": mpi,
            "omp_threads": threads,
            "repetitions": len(values),
            "solve_mean_s": f"{statistics.mean(solve):.9g}",
            "solve_min_s": f"{min(solve):.9g}",
            "solve_max_s": f"{max(solve):.9g}",
            "solve_stddev_s": f"{statistics.stdev(solve) if len(solve) > 1 else 0.0:.9g}",
            "iterations_mean": f"{statistics.mean(iterations):.9g}",
            "relative_residual_max": f"{max(residual):.9g}",
            "solution_error_mean": f"{statistics.mean(errors):.9g}",
            "padding_overhead": f"{statistics.mean(padding):.9g}",
        })

print(f"{len(rows)} resultados agrupados em {len(groups)} grupos: {output_path}")
