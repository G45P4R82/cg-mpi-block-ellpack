#!/usr/bin/env python3
"""Gera CSV e graficos de escalabilidade por numero de nos."""

import csv
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


run_dir = Path(sys.argv[1])
output_csv = Path(sys.argv[2] if len(sys.argv) > 2 else "results/processed/cg_node_scaling_tvbox.csv")
plots_dir = Path(sys.argv[3] if len(sys.argv) > 3 else "results/plots/tvbox-nodes")
output_csv.parent.mkdir(parents=True, exist_ok=True)
plots_dir.mkdir(parents=True, exist_ok=True)

pattern = re.compile(r"^([a-z_]+)=(.*)$", re.MULTILINE)

# Le a fila original para saber node_count declarado por id
queue_file = Path("experiments/node-scaling.tsv")
declared_nodes = {}
if queue_file.exists():
    with queue_file.open() as stream:
        next(stream)  # header
        for line in stream:
            parts = line.strip().split("\t")
            if len(parts) >= 7:
                declared_nodes[parts[0]] = int(parts[6])

rows = []
for item_dir in sorted(run_dir.iterdir()):
    if not item_dir.is_dir():
        continue
    log_path = item_dir / "launcher.log"
    placement_path = item_dir / "pod-placement.txt"
    if not log_path.exists():
        continue
    text = log_path.read_text(errors="replace")
    values = dict(pattern.findall(text))
    if "solve_time_s" not in values:
        continue
    placement = placement_path.read_text(errors="replace") if placement_path.exists() else ""
    worker_nodes = sorted({node for name, node in (pair.split("=", 1) for pair in placement.strip(";").split(";") if "=" in pair) if "worker" in name and node})
    row = {
        "id": item_dir.name,
        "matrix": values.get("matrix", "").split("/")[-1].split(".")[0],
        "block_size": int(values["block_size"]),
        "mpi_processes": int(values["mpi_processes"]),
        "omp_threads": int(values["omp_threads"]),
        "solve_time_s": float(values["solve_time_s"]),
        "read_time_s": float(values.get("read_time_s", "0")),
        "conversion_time_s": float(values.get("conversion_time_s", "0")),
        "iterations": int(values["iterations"]),
        "relative_residual": float(values["relative_residual"]),
        "solution_error": float(values["solution_error"]),
        "padding_overhead": float(values["padding_overhead"]),
        "worker_nodes_observed": ",".join(worker_nodes),
        "node_count": declared_nodes.get(item_dir.name, len(worker_nodes) or 1),
    }
    rows.append(row)

if not rows:
    raise SystemExit("Nenhum log valido encontrado em " + str(run_dir))

groups = defaultdict(list)
for row in rows:
    key = (row["node_count"], row["mpi_processes"], row["omp_threads"])
    groups[key].append(row)

# baseline: 1 no, 2 processos, 1 thread
baseline_key = (1, 2, 1)
baseline_time = None
if baseline_key in groups:
    baseline_time = statistics.mean(r["solve_time_s"] for r in groups[baseline_key])

aggregated = []
for key, items in sorted(groups.items()):
    nc, mpi, threads = key
    solve = [r["solve_time_s"] for r in items]
    mean = statistics.mean(solve)
    stddev = statistics.stdev(solve) if len(solve) > 1 else 0.0
    speedup = baseline_time / mean if baseline_time else ""
    efficiency = (speedup / nc) if isinstance(speedup, float) else ""
    aggregated.append({
        "node_count": nc,
        "mpi_processes": mpi,
        "omp_threads": threads,
        "repetitions": len(items),
        "solve_mean_s": mean,
        "solve_min_s": min(solve),
        "solve_max_s": max(solve),
        "solve_stddev_s": stddev,
        "iterations_mean": statistics.mean(r["iterations"] for r in items),
        "relative_residual_max": max(r["relative_residual"] for r in items),
        "speedup": speedup,
        "efficiency": efficiency,
        "worker_nodes_sample": items[0]["worker_nodes_observed"],
    })

fields = [
    "node_count", "mpi_processes", "omp_threads", "repetitions",
    "solve_mean_s", "solve_min_s", "solve_max_s", "solve_stddev_s",
    "iterations_mean", "relative_residual_max",
    "speedup", "efficiency", "worker_nodes_sample",
]
with output_csv.open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in aggregated:
        formatted = {}
        for field in fields:
            value = row[field]
            formatted[field] = f"{value:.9g}" if isinstance(value, float) else value
        writer.writerow(formatted)

print(f"{len(rows)} execucoes, {len(groups)} configuracoes, agregados em {output_csv}")

# Grafico tempo por nos para a configuracao MPI=4
fig, axis = plt.subplots()
mpi4 = sorted((r for r in aggregated if r["mpi_processes"] == 4), key=lambda r: r["node_count"])
mpi2 = sorted((r for r in aggregated if r["mpi_processes"] == 2), key=lambda r: r["node_count"])
if mpi4:
    axis.errorbar(
        [r["node_count"] for r in mpi4],
        [r["solve_mean_s"] for r in mpi4],
        yerr=[r["solve_stddev_s"] for r in mpi4],
        marker="o", capsize=4, label="MPI=4",
    )
    for r in mpi4:
        axis.annotate(
            f"{r['node_count']} no(s)\n{r['solve_mean_s']:.3f}s",
            (r["node_count"], r["solve_mean_s"]),
            xytext=(5, 8), textcoords="offset points", fontsize=7,
            bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#999", "alpha": 0.85},
        )
if mpi2:
    axis.errorbar(
        [r["node_count"] for r in mpi2],
        [r["solve_mean_s"] for r in mpi2],
        yerr=[r["solve_stddev_s"] for r in mpi2],
        marker="s", capsize=4, label="MPI=2",
    )
axis.set_xlabel("Numero de nos distintos")
axis.set_ylabel("Tempo medio de solucao (s)")
axis.set_title("Escalabilidade por nos\nbcsstk16, block 8")
axis.grid(alpha=0.25)
axis.legend()
fig.tight_layout()
fig.savefig(plots_dir / "time_by_nodes.png", dpi=160)
plt.close(fig)

# Grafico speedup e eficiencia (MPI=4)
if mpi4 and all(isinstance(r["speedup"], float) for r in mpi4):
    fig, axis = plt.subplots()
    axis.plot([r["node_count"] for r in mpi4], [r["speedup"] for r in mpi4], "o-", label="Speedup")
    axis.plot([r["node_count"] for r in mpi4], [r["efficiency"] for r in mpi4], "s-", label="Eficiencia")
    axis.plot([r["node_count"] for r in mpi4], [r["node_count"] for r in mpi4], "--", color="gray", label="Ideal")
    for r in mpi4:
        axis.annotate(
            f"{r['node_count']} no(s)\nS={r['speedup']:.3f}\nE={r['efficiency']:.3f}",
            (r["node_count"], r["speedup"]),
            xytext=(5, 8), textcoords="offset points", fontsize=7,
            bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#999", "alpha": 0.85},
        )
    axis.set_xlabel("Numero de nos distintos")
    axis.set_ylabel("Fator")
    axis.set_title("Speedup e eficiencia por nos\nReferencia: 1 no, MPI=2")
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "speedup_efficiency_by_nodes.png", dpi=160)
    plt.close(fig)

print(f"graficos em {plots_dir}")
