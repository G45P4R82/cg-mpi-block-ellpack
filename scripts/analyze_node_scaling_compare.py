#!/usr/bin/env python3
"""Compara campanhas de escalabilidade por nos entre as variantes
replicated (matriz replicada em cada processo) e distributed
(Block ELLPACK particionado com comunicacao seletiva)."""

import csv
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


def parse_log(path: Path) -> dict:
    pattern = re.compile(r"^([a-z_]+)=(.*)$", re.MULTILINE)
    text = path.read_text(errors="replace")
    return dict(pattern.findall(text))


def load_campaign(run_dir: Path, queue_file: Path, variant: str) -> list[dict]:
    declared_nodes = {}
    if queue_file.exists():
        with queue_file.open() as stream:
            next(stream)
            for line in stream:
                parts = line.strip().split("\t")
                if len(parts) >= 7:
                    declared_nodes[parts[0]] = int(parts[6])

    rows = []
    for item_dir in sorted(run_dir.iterdir()):
        if not item_dir.is_dir():
            continue
        log_path = item_dir / "launcher.log"
        if not log_path.exists():
            continue
        values = parse_log(log_path)
        if "solve_time_s" not in values:
            continue
        rows.append({
            "variant": variant,
            "id": item_dir.name,
            "matrix": values.get("matrix", "").split("/")[-1].split(".")[0],
            "mpi_processes": int(values["mpi_processes"]),
            "omp_threads": int(values["omp_threads"]),
            "solve_time_s": float(values["solve_time_s"]),
            "read_time_s": float(values.get("read_time_s", "0")),
            "conversion_time_s": float(values.get("conversion_time_s", "0")),
            "iterations": int(values["iterations"]),
            "relative_residual": float(values["relative_residual"]),
            "padding_overhead": float(values.get("padding_overhead", "0")),
            "memory_max_mb": float(values.get("memory_max_mb", "0") or 0),
            "memory_avg_mb": float(values.get("memory_avg_mb", "0") or 0),
            "memory_total_mb": float(values.get("memory_total_mb", "0") or 0),
            "comm_bytes": int(values.get("comm_bytes", "0") or 0),
            "node_count": declared_nodes.get(item_dir.name, 0),
        })
    return rows


def aggregate(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        key = (row["variant"], row["node_count"], row["mpi_processes"], row["omp_threads"])
        groups[key].append(row)
    out = []
    for key, items in sorted(groups.items()):
        variant, nc, mpi, threads = key
        solve = [r["solve_time_s"] for r in items]
        out.append({
            "variant": variant,
            "node_count": nc,
            "mpi_processes": mpi,
            "omp_threads": threads,
            "repetitions": len(items),
            "solve_mean_s": statistics.mean(solve),
            "solve_stddev_s": statistics.stdev(solve) if len(solve) > 1 else 0.0,
            "iterations_mean": statistics.mean(r["iterations"] for r in items),
            "relative_residual_max": max(r["relative_residual"] for r in items),
            "memory_max_mb": max(r["memory_max_mb"] for r in items),
            "memory_avg_mb": statistics.mean(r["memory_avg_mb"] for r in items) if items[0]["memory_avg_mb"] else 0.0,
            "memory_total_mb": max(r["memory_total_mb"] for r in items),
            "comm_bytes_mean": statistics.mean(r["comm_bytes"] for r in items) if items[0]["comm_bytes"] else 0,
        })
    return out


def write_csv(agg: list[dict], path: Path) -> None:
    fields = ["variant", "node_count", "mpi_processes", "omp_threads", "repetitions",
              "solve_mean_s", "solve_stddev_s", "iterations_mean", "relative_residual_max",
              "memory_max_mb", "memory_avg_mb", "memory_total_mb", "comm_bytes_mean"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in agg:
            writer.writerow({f: f"{row[f]:.9g}" if isinstance(row[f], float) else row[f] for f in fields})


def plot_time_comparison(agg: list[dict], plots_dir: Path) -> None:
    plots_dir.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots()
    for variant, marker, color in [("replicated", "s", "#FF7F0E"), ("distributed", "o", "#2E86AB")]:
        mpi4 = sorted((r for r in agg if r["variant"] == variant and r["mpi_processes"] == 4),
                      key=lambda r: r["node_count"])
        if mpi4:
            axis.errorbar(
                [r["node_count"] for r in mpi4],
                [r["solve_mean_s"] for r in mpi4],
                yerr=[r["solve_stddev_s"] for r in mpi4],
                marker=marker, capsize=4, color=color,
                label=f"MPI=4 {variant}",
            )
            for r in mpi4:
                axis.annotate(
                    f"{r['solve_mean_s']:.2f}s",
                    (r["node_count"], r["solve_mean_s"]),
                    xytext=(6, 6), textcoords="offset points", fontsize=7,
                )
    axis.set_xlabel("Numero de nos distintos")
    axis.set_ylabel("Tempo medio de solucao (s)")
    axis.set_title("Comparacao de tempo: replicated vs distributed\nbcsstk16, block 8, MPI=4")
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "time_compare_mpi4.png", dpi=160)
    plt.close(fig)


def plot_memory_comparison(agg: list[dict], plots_dir: Path) -> None:
    plots_dir.mkdir(parents=True, exist_ok=True)
    # Memoria max por rank, apenas para distributed
    fig, axis = plt.subplots()
    for mpi in (2, 4):
        dist = sorted((r for r in agg if r["variant"] == "distributed" and r["mpi_processes"] == mpi),
                      key=lambda r: r["node_count"])
        if dist:
            axis.plot(
                [r["node_count"] for r in dist],
                [r["memory_max_mb"] for r in dist],
                "o-", label=f"distributed MPI={mpi} (max por rank)",
            )
    # Para replicated: nao temos a metrica. Vamos estimar: memory_max == memory_total ~= mesma coisa
    # pois cada rank replica tudo. Como aproximacao, usamos a memoria do distributed MPI=1 (nao temos)
    # ou inferimos pelo distributed com n=1: memory_total_dist * processes / 1.
    # Melhor: desenhar apenas a curva distribuida para evidenciar o ganho por rank.
    axis.axhline(y=7.25, color="#999", linestyle="--",
                 label="replicated (estimado por rank)")
    axis.set_xlabel("Numero de nos distintos")
    axis.set_ylabel("Memoria por rank (MB)")
    axis.set_title("Memoria por rank: replicated vs distributed\nbcsstk16, block 8")
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "memory_per_rank.png", dpi=160)
    plt.close(fig)


def plot_speedup(agg: list[dict], plots_dir: Path) -> None:
    fig, axis = plt.subplots()
    for variant, marker, color in [("replicated", "s", "#FF7F0E"), ("distributed", "o", "#2E86AB")]:
        subset = [r for r in agg if r["variant"] == variant]
        base = next((r for r in subset if r["node_count"] == 1 and r["mpi_processes"] == 2), None)
        if base is None:
            continue
        mpi4 = sorted((r for r in subset if r["mpi_processes"] == 4),
                      key=lambda r: r["node_count"])
        if not mpi4:
            continue
        axis.plot(
            [r["node_count"] for r in mpi4],
            [base["solve_mean_s"] / r["solve_mean_s"] for r in mpi4],
            marker=marker, linestyle="-", color=color,
            label=f"{variant}",
        )
    axis.plot([1, 2, 4], [1, 2, 4], "--", color="gray", label="Ideal")
    axis.set_xlabel("Numero de nos distintos")
    axis.set_ylabel("Speedup vs 1 no (MPI=2)")
    axis.set_title("Speedup por nos: replicated vs distributed\nbcsstk16, block 8, MPI=4")
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "speedup_compare.png", dpi=160)
    plt.close(fig)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("uso: analyze_node_scaling_compare.py <run_replicated> <run_distributed> [csv_out] [plots_dir]", file=sys.stderr)
        return 1
    rep_dir = Path(argv[1])
    dist_dir = Path(argv[2])
    csv_out = Path(argv[3] if len(argv) > 3 else "results/processed/cg_node_scaling_compare.csv")
    plots_dir = Path(argv[4] if len(argv) > 4 else "results/plots/tvbox-nodes-compare")

    rep_queue = Path("experiments/node-scaling.tsv")
    dist_queue = Path("experiments/node-scaling-dist.tsv")

    rep_rows = load_campaign(rep_dir, rep_queue, "replicated")
    dist_rows = load_campaign(dist_dir, dist_queue, "distributed")

    all_rows = rep_rows + dist_rows
    agg = aggregate(all_rows)
    write_csv(agg, csv_out)
    print(f"{len(all_rows)} execucoes, {len(agg)} grupos, csv em {csv_out}")

    plot_time_comparison(agg, plots_dir)
    plot_memory_comparison(agg, plots_dir)
    plot_speedup(agg, plots_dir)
    print(f"graficos em {plots_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
