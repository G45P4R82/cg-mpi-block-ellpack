#!/usr/bin/env python3
"""Gera metricas e graficos a partir da campanha CG processada."""

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


input_path = Path(sys.argv[1] if len(sys.argv) > 1 else "results/processed/cg_results_tvbox.csv")
output_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "results/processed")
plots_dir = Path(sys.argv[3] if len(sys.argv) > 3 else "results/plots/tvbox")
output_dir.mkdir(parents=True, exist_ok=True)
plots_dir.mkdir(parents=True, exist_ok=True)

with input_path.open(newline="") as stream:
    rows = list(csv.DictReader(stream))

groups = defaultdict(list)
for row in rows:
    key = (row["family"], row["matrix"], row["block_size"], row["mpi_processes"], row["omp_threads"])
    groups[key].append(row)

stats = []
for key, values in sorted(groups.items()):
    family, matrix, block, mpi, threads = key
    solve = [float(row["solve_time_s"]) for row in values]
    stats.append({
        "family": family,
        "matrix": matrix,
        "block_size": int(block),
        "mpi_processes": int(mpi),
        "omp_threads": int(threads),
        "repetitions": len(values),
        "solve_mean_s": statistics.mean(solve),
        "solve_min_s": min(solve),
        "solve_max_s": max(solve),
        "solve_stddev_s": statistics.stdev(solve) if len(solve) > 1 else 0.0,
        "padding_overhead": float(values[0]["padding_overhead"]),
        "relative_residual_max": max(float(row["relative_residual"]) for row in values),
    })

strong_baseline = next(row["solve_mean_s"] for row in stats if row["family"] == "strong" and row["mpi_processes"] == 1)
hybrid_baseline = next(row["solve_mean_s"] for row in stats if row["family"] == "hybrid" and row["omp_threads"] == 1)
for row in stats:
    row["speedup"] = ""
    row["efficiency"] = ""
    if row["family"] == "strong":
        row["speedup"] = strong_baseline / row["solve_mean_s"]
        row["efficiency"] = row["speedup"] / row["mpi_processes"]
    elif row["family"] == "hybrid":
        row["speedup"] = hybrid_baseline / row["solve_mean_s"]
        row["efficiency"] = row["speedup"] / row["omp_threads"]

metrics_path = output_dir / "cg_metrics_tvbox.csv"
fields = [
    "family", "matrix", "block_size", "mpi_processes", "omp_threads", "repetitions",
    "solve_mean_s", "solve_min_s", "solve_max_s", "solve_stddev_s", "speedup",
    "efficiency", "padding_overhead", "relative_residual_max",
]
with metrics_path.open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in stats:
        writer.writerow({field: (f"{row[field]:.9g}" if isinstance(row[field], float) else row[field]) for field in fields})

base = [row for row in stats if row["family"] == "base"]
for matrix in sorted({row["matrix"] for row in base}):
    values = sorted((row for row in base if row["matrix"] == matrix), key=lambda row: row["block_size"])
    plt.errorbar(
        [row["block_size"] for row in values],
        [row["solve_mean_s"] for row in values],
        yerr=[row["solve_stddev_s"] for row in values],
        marker="o",
        capsize=4,
        label=matrix,
    )
plt.xlabel("Block size")
plt.ylabel("Tempo medio de solucao (s)")
plt.title("Tempo por block size")
plt.grid(alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(plots_dir / "solve_time_by_block.png", dpi=160)
plt.close()

strong = sorted((row for row in stats if row["family"] == "strong"), key=lambda row: row["mpi_processes"])
plt.errorbar(
    [row["mpi_processes"] for row in strong],
    [row["solve_mean_s"] for row in strong],
    yerr=[row["solve_stddev_s"] for row in strong],
    marker="o",
    capsize=4,
)
plt.xlabel("Processos MPI")
plt.ylabel("Tempo medio de solucao (s)")
plt.title("Strong scaling: bcsstk16, block 8")
plt.grid(alpha=0.25)
plt.tight_layout()
plt.savefig(plots_dir / "strong_scaling_time.png", dpi=160)
plt.close()

fig, axis = plt.subplots()
axis.plot([row["mpi_processes"] for row in strong], [row["speedup"] for row in strong], "o-", label="Speedup")
axis.plot([row["mpi_processes"] for row in strong], [row["efficiency"] for row in strong], "s-", label="Eficiencia")
axis.set_xlabel("Processos MPI")
axis.set_ylabel("Fator")
axis.set_title("Strong scaling: speedup e eficiencia")
axis.set_xticks([row["mpi_processes"] for row in strong])
axis.grid(alpha=0.25)
axis.legend()
fig.tight_layout()
fig.savefig(plots_dir / "strong_scaling_speedup_efficiency.png", dpi=160)
plt.close(fig)

hybrid = sorted((row for row in stats if row["family"] == "hybrid"), key=lambda row: row["omp_threads"])
fig, axis = plt.subplots()
axis.plot([row["omp_threads"] for row in hybrid], [row["speedup"] for row in hybrid], "o-", label="Speedup")
axis.plot([row["omp_threads"] for row in hybrid], [row["efficiency"] for row in hybrid], "s-", label="Eficiencia")
axis.set_xlabel("Threads OpenMP")
axis.set_ylabel("Fator")
axis.set_title("Escala hibrida: speedup e eficiencia")
axis.set_xticks([row["omp_threads"] for row in hybrid])
axis.grid(alpha=0.25)
axis.legend()
fig.tight_layout()
fig.savefig(plots_dir / "hybrid_scaling_speedup_efficiency.png", dpi=160)
plt.close(fig)

for matrix in sorted({row["matrix"] for row in base}):
    values = sorted((row for row in base if row["matrix"] == matrix), key=lambda row: row["block_size"])
    plt.plot([row["block_size"] for row in values], [row["padding_overhead"] * 100 for row in values], "o-", label=matrix)
plt.xlabel("Block size")
plt.ylabel("Padding (%)")
plt.title("Overhead de padding do Block ELLPACK")
plt.grid(alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(plots_dir / "padding_by_block.png", dpi=160)
plt.close()

print(f"{len(rows)} registros, {len(stats)} grupos, metricas em {metrics_path}")
print(f"graficos em {plots_dir}")
