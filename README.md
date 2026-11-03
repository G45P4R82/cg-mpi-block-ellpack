# Projeto Final: Gradiente Conjugado Distribuido

Implementacao e avaliacao do metodo do Gradiente Conjugado para sistemas
lineares esparsos, simetricos e definidos positivos, usando armazenamento
Block ELLPACK, MPI entre processos e OpenMP/BLAS dentro de cada processo.

## Matrizes

Tres matrizes SuiteSparse foram preservadas em `matrices/`:

- `bcsstk34`;
- `bcsstk14`;
- `bcsstk16`.

Os metadados, fontes e SHA-256 estao em `matrices/README.md`.

## Estrutura

```text
src/        implementacao Matrix Market, Block ELLPACK e CG MPI
include/    headers compartilhados
scripts/    conversao, execucao, parsing e graficos
jobs/       scripts PBS
matrices/   entradas Matrix Market
results/    logs, CSVs e figuras
report/     relatorio e modelo de conclusao
docs/       plano, formato e validacao
```

Leia [`AGENT_HANDOFF.md`](AGENT_HANDOFF.md) antes de implementar.
