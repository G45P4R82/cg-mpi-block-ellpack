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


def annotate_point(axis, x, y, label, offset):
    axis.annotate(
        label,
        (x, y),
        xytext=offset,
        textcoords="offset points",
        fontsize=7,
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#999999", "alpha": 0.85},
        arrowprops={"arrowstyle": "->", "alpha": 0.45},
    )


def add_story(fig, text):
    fig.text(0.02, 0.015, text, fontsize=8.5, color="#333333")


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
    for index, row in enumerate(values):
        descriptions = [
            "bloco pequeno reduz zeros e tempo",
            "bloco intermediario equilibra acesso e armazenamento",
            "padding crescente aumenta trabalho e memoria",
            "bloco grande amplia zeros e custo",
        ]
        annotate_point(
            axis,
            row["block_size"],
            row["solve_mean_s"],
            f"b={row['block_size']} | {row['solve_mean_s']:.3f}s\npad={row['padding_overhead'] * 100:.1f}%\n{descriptions[index]}",
            (4, 8 if index % 2 == 0 else -38),
        )
axis.set_xlabel("Block size")
axis.set_ylabel("Tempo medio de solucao (s)")
axis.set_title("Tempo por block size\nCada ponto = media de 3 execucoes")
axis.grid(alpha=0.25)
axis.legend()
add_story(fig, "Leitura: inicio = bloco 4; durante = blocos 8/16; fim = bloco 32. O padding indica zeros adicionados pelo Block ELLPACK.")
fig.tight_layout(rect=(0, 0.07, 1, 1))
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
for index, row in enumerate(strong):
    descriptions = [
        "referencia sem comunicacao MPI extra",
        "mais comunicacao produz pouco ganho",
        "overhead MPI domina e tempo aumenta",
    ]
    annotate_point(
        axis,
        row["mpi_processes"],
        row["solve_mean_s"],
        f"MPI={row['mpi_processes']} | {row['solve_mean_s']:.3f}s\n{descriptions[index]}",
        (-48, 10 if index % 2 == 0 else -35),
    )
axis.set_xlabel("Processos MPI")
axis.set_ylabel("Tempo medio de solucao (s)")
axis.set_title("Strong scaling: bcsstk16, block 8\nCada ponto = media de 3 execucoes")
axis.grid(alpha=0.25)
add_story(fig, "Leitura: inicio = 1 processo; durante = 2; fim = 4. O tempo cresce porque a sincronizacao MPI custa mais que o paralelismo ganho.")
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(plots_dir / "strong_scaling_time.png", dpi=160)
plt.close(fig)

fig, axis = plt.subplots()
axis.plot([row["mpi_processes"] for row in strong], [row["speedup"] for row in strong], "o-", label="Speedup")
axis.plot([row["mpi_processes"] for row in strong], [row["efficiency"] for row in strong], "s-", label="Eficiencia")
axis.plot([row["mpi_processes"] for row in strong], [row["mpi_processes"] for row in strong], "--", color="gray", label="Ideal")
for index, row in enumerate(strong):
    descriptions = [
        "referencia: speedup e eficiencia ideais",
        "comunicacao reduz o ganho esperado",
        "mais processos diminuem eficiencia final",
    ]
    annotate_point(
        axis,
        row["mpi_processes"],
        row["speedup"],
        f"MPI={row['mpi_processes']} | S={row['speedup']:.3f}x\nE={row['efficiency']:.3f}\n{descriptions[index]}",
        (-42, 10 if index % 2 == 0 else -38),
    )
axis.set_xlabel("Processos MPI")
axis.set_ylabel("Fator")
axis.set_title("Strong scaling: speedup e eficiencia\nCirculos = speedup | quadrados = eficiencia")
axis.set_xticks([row["mpi_processes"] for row in strong])
axis.grid(alpha=0.25)
axis.legend()
add_story(fig, "Leitura: a linha pontilhada e o ideal; a distancia entre ela e os circulos mostra o overhead MPI. A eficiencia usa a escala da direita conceitual: 1,0 = 100%.")
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(plots_dir / "strong_scaling_speedup_efficiency.png", dpi=160)
plt.close(fig)

hybrid = sorted((row for row in stats if row["family"] == "hybrid"), key=lambda row: row["omp_threads"])
fig, axis = plt.subplots()
axis.plot([row["omp_threads"] for row in hybrid], [row["speedup"] for row in hybrid], "o-", label="Speedup")
axis.plot([row["omp_threads"] for row in hybrid], [row["efficiency"] for row in hybrid], "s-", label="Eficiencia")
axis.plot([row["omp_threads"] for row in hybrid], [row["omp_threads"] for row in hybrid], "--", color="gray", label="Ideal")
for index, row in enumerate(hybrid):
    descriptions = [
        "referencia: uma thread processa tudo",
        "duas threads reduzem tempo efetivo",
        "quatro threads melhoram, eficiencia cai",
    ]
    annotate_point(
        axis,
        row["omp_threads"],
        row["speedup"],
        f"T={row['omp_threads']} | S={row['speedup']:.3f}x\nE={row['efficiency']:.3f}\n{descriptions[index]}",
        (-42, 10 if index % 2 == 0 else -42),
    )
axis.set_xlabel("Threads OpenMP")
axis.set_ylabel("Fator")
axis.set_title("Escala hibrida: speedup e eficiencia\nMPI fixo em 2 processos")
axis.set_xticks([row["omp_threads"] for row in hybrid])
axis.grid(alpha=0.25)
axis.legend()
add_story(fig, "Leitura: inicio = 1 thread; durante = 2; fim = 4. O speedup cresce, mas fica abaixo do ideal porque as threads disputam memoria.")
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(plots_dir / "hybrid_scaling_speedup_efficiency.png", dpi=160)
plt.close(fig)

fig, axis = plt.subplots()
for matrix in sorted({row["matrix"] for row in base}):
    values = sorted((row for row in base if row["matrix"] == matrix), key=lambda row: row["block_size"])
    axis.plot([row["block_size"] for row in values], [row["padding_overhead"] * 100 for row in values], "o-", label=matrix)
    for index, row in enumerate(values):
        descriptions = [
            "bloco pequeno: menos zeros adicionados",
            "bloco intermediario: padding comeca crescer",
            "bloco maior: mais zeros armazenados",
            "bloco grande: alto desperdicio de memoria",
        ]
        annotate_point(
            axis,
            row["block_size"],
            row["padding_overhead"] * 100,
            f"b={row['block_size']} | pad={row['padding_overhead'] * 100:.1f}%\n{descriptions[index]}",
            (4, 8 if index % 2 == 0 else -32),
        )
axis.set_xlabel("Block size")
axis.set_ylabel("Padding (%)")
axis.set_title("Overhead de padding do Block ELLPACK\nCada ponto = zeros adicionais na representacao")
axis.grid(alpha=0.25)
axis.legend()
add_story(fig, "Leitura: inicio = bloco 4; durante = 8/16; fim = 32. Quanto maior o padding, mais memoria e leituras nao uteis no SpMV.")
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(plots_dir / "padding_by_block.png", dpi=160)
plt.close(fig)

print(f"{len(rows)} registros, {len(stats)} grupos, metricas em {metrics_path}")
print(f"graficos em {plots_dir}")
