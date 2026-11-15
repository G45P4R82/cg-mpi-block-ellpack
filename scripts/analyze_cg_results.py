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
fig, axis = plt.subplots()
for matrix in sorted({row["matrix"] for row in base}):
    values = sorted((row for row in base if row["matrix"] == matrix), key=lambda row: row["block_size"])
    axis.errorbar(
        [row["block_size"] for row in values],
        [row["solve_mean_s"] for row in values],
        yerr=[row["solve_stddev_s"] for row in values],
        marker="o",
        capsize=4,
        label=matrix,
    )
    best = min(values, key=lambda row: row["solve_mean_s"])
    axis.annotate(
        f"melhor: bloco {best['block_size']}",
        (best["block_size"], best["solve_mean_s"]),
        xytext=(5, 8),
        textcoords="offset points",
        fontsize=8,
        arrowprops={"arrowstyle": "->", "alpha": 0.5},
    )
axis.set_xlabel("Block size")
axis.set_ylabel("Tempo medio de solucao (s)")
axis.set_title("Tempo por block size\nBlocos menores vencem por reduzir padding")
axis.grid(alpha=0.25)
axis.legend()
fig.tight_layout()
fig.savefig(plots_dir / "solve_time_by_block.png", dpi=160)
plt.close(fig)

strong = sorted((row for row in stats if row["family"] == "strong"), key=lambda row: row["mpi_processes"])
fig, axis = plt.subplots()
axis.errorbar(
    [row["mpi_processes"] for row in strong],
    [row["solve_mean_s"] for row in strong],
    yerr=[row["solve_stddev_s"] for row in strong],
    marker="o",
    capsize=4,
)
axis.annotate(
    "mais processos nao ajudam\n neste tamanho de matriz",
    (strong[-1]["mpi_processes"], strong[-1]["solve_mean_s"]),
    xytext=(-105, 20),
    textcoords="offset points",
    fontsize=8,
    arrowprops={"arrowstyle": "->", "alpha": 0.5},
)
axis.set_xlabel("Processos MPI")
axis.set_ylabel("Tempo medio de solucao (s)")
axis.set_title("Strong scaling: bcsstk16, block 8\nA comunicacao supera o paralelismo")
axis.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(plots_dir / "strong_scaling_time.png", dpi=160)
plt.close(fig)

fig, axis = plt.subplots()
axis.plot([row["mpi_processes"] for row in strong], [row["speedup"] for row in strong], "o-", label="Speedup")
axis.plot([row["mpi_processes"] for row in strong], [row["efficiency"] for row in strong], "s-", label="Eficiencia")
axis.plot([row["mpi_processes"] for row in strong], [row["mpi_processes"] for row in strong], "--", color="gray", label="Ideal")
axis.annotate("speedup abaixo do ideal\n(overhead MPI)", (4, strong[-1]["speedup"]), xytext=(-110, -35), textcoords="offset points", fontsize=8, arrowprops={"arrowstyle": "->", "alpha": 0.5})
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
axis.plot([row["omp_threads"] for row in hybrid], [row["omp_threads"] for row in hybrid], "--", color="gray", label="Ideal")
axis.annotate("ganho real: 1,447x\ncom 4 threads", (4, hybrid[-1]["speedup"]), xytext=(-105, 18), textcoords="offset points", fontsize=8, arrowprops={"arrowstyle": "->", "alpha": 0.5})
axis.set_xlabel("Threads OpenMP")
axis.set_ylabel("Fator")
axis.set_title("Escala hibrida: speedup e eficiencia")
axis.set_xticks([row["omp_threads"] for row in hybrid])
axis.grid(alpha=0.25)
axis.legend()
fig.tight_layout()
fig.savefig(plots_dir / "hybrid_scaling_speedup_efficiency.png", dpi=160)
plt.close(fig)

fig, axis = plt.subplots()
for matrix in sorted({row["matrix"] for row in base}):
    values = sorted((row for row in base if row["matrix"] == matrix), key=lambda row: row["block_size"])
    axis.plot([row["block_size"] for row in values], [row["padding_overhead"] * 100 for row in values], "o-", label=matrix)
    lowest = min(values, key=lambda row: row["padding_overhead"])
    axis.annotate(f"min {lowest['padding_overhead'] * 100:.1f}%", (lowest["block_size"], lowest["padding_overhead"] * 100), xytext=(5, 8), textcoords="offset points", fontsize=8)
axis.set_xlabel("Block size")
axis.set_ylabel("Padding (%)")
axis.set_title("Overhead de padding do Block ELLPACK\nBlocos maiores preenchem mais zeros")
axis.grid(alpha=0.25)
axis.legend()
fig.tight_layout()
fig.savefig(plots_dir / "padding_by_block.png", dpi=160)
plt.close(fig)

print(f"{len(rows)} registros, {len(stats)} grupos, metricas em {metrics_path}")
print(f"graficos em {plots_dir}")
