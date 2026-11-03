#!/usr/bin/env python3
import csv
import re
import sys
from pathlib import Path

raw_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "results/raw")
output = Path(sys.argv[2] if len(sys.argv) > 2 else "results/processed/cg_results.csv")
output.parent.mkdir(parents=True, exist_ok=True)
rows = []
pattern = re.compile(r"^([a-z_]+)=(.*)$", re.MULTILINE)
for path in sorted(raw_dir.rglob("*.log")):
    text = path.read_text(errors="replace")
    values = dict(pattern.findall(text))
    if "solve_time_s" not in values:
        continue
    match = re.search(r"cg-(bcsstk\d+)-b(\d+)-p(\d+)-t(\d+)-r(\d+)", path.name)
    if not match:
        continue
    matrix, block, mpi, threads, repeat = match.groups()
    values.update({
        "matrix": matrix,
        "block_size": int(block),
        "mpi_processes": int(mpi),
        "omp_threads": int(threads),
        "repeat": int(repeat),
        "source": str(path),
    })
    rows.append(values)

if not rows:
    raise SystemExit("Nenhum log CG bem-sucedido encontrado")
fields = sorted({field for row in rows for field in row})
with output.open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print(f"{len(rows)} resultados salvos em {output}")
