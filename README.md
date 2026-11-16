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

## Problema Resolvido

O programa resolve `A x = b`. As matrizes sao modelos numericos de rigidez
estrutural: linhas e colunas representam graus de liberdade e os valores
representam interacoes entre esses graus. Para validar o solver, usamos:

```text
x_true = [1, 1, ..., 1]
b = A * x_true
x_0 = [0, 0, ..., 0]
```

O Gradiente Conjugado parte de `x_0` e tenta reconstruir `x_true`.

As matrizes usam Matrix Market `coordinate real symmetric` e armazenam apenas
a parte triangular. O parser expande a simetria sem duplicar a diagonal.

| Matriz | Problema | Dimensao | Entradas no arquivo | `nnz` expandido |
|---|---|---:|---:|---:|
| `bcsstk34` | Flambagem NASTRAN da Boeing | 588 x 588 | 11.003 | 21.418 |
| `bcsstk14` | Rigidez do teto do Omni Coliseum | 1.806 x 1.806 | 32.630 | 63.454 |
| `bcsstk16` | Rigidez de uma barragem | 4.884 x 4.884 | 147.631 | 290.378 |

## Compilacao

Em um ambiente com MPI e OpenBLAS:

```bash
make CXX=mpicxx BLAS_LIBS=-lopenblas
```

Para construir a imagem ARM64:

```bash
docker buildx build --platform linux/arm64 \
  -t srmarinho/cg-mpi:arm64 --push .
```

## Execucao Individual

```bash
mpirun -n 2 ./bin/cg_mpi \
  --matrix matrices/bcsstk34/bcsstk34.mtx \
  --block-size 8 --threads 2 --tol 1e-8 --max-iters 10000
```

Cada execucao informa leitura, conversao, solucao, iteracoes, residuo
relativo, erro em relacao a `x_true` e padding do Block ELLPACK.

## Paralelismo E Comunicacao

O particionamento distribui intervalos de linhas entre processos MPI.
`MPI_Allgatherv` disponibiliza o vetor global para o SpMV e `MPI_Allreduce`
calcula os produtos escalares globais. Dentro de cada processo, SpMV,
produtos escalares e atualizacoes de `x`, `r` e `p` usam OpenMP.

## Fila De Experimentos

A fila estatica com 54 configuracoes esta em `experiments/queue.tsv`. Cada
linha possui ID, matriz, block size, MPI, OpenMP, repeticao e familia.

```bash
KUBE_CONTEXT=tvbox-k3s K8S_NAMESPACE=hpc-cg \
  RUN_DIR=results/queue-tvbox bash scripts/run_queue.sh
```

O runner executa um MPIJob por vez, salva manifesto e log por ID e retoma sem
repetir itens `SUCCESS`.

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

## Campanha Realizada

A campanha final foi executada no cluster TVBox, contexto `tvbox-k3s`, com MPI
Operator v0.8.2:

```text
36 execucoes de block size
9 execucoes de strong scaling MPI
9 execucoes de escala hibrida MPI/OpenMP
54 execucoes no total
3 repeticoes por configuracao
```

Todos os 54 casos foram concluidos com sucesso e residuo relativo abaixo de
`1e-8`.

Resultados processados:

```text
results/processed/cg_results_tvbox.csv
results/processed/cg_stats_tvbox.csv
results/processed/cg_metrics_tvbox.csv
results/plots/tvbox/
```

Logs e manifestos da campanha final:

```text
results/raw/cg-campaign-tvbox-full-20261115T171915Z/
```

## Requisitos Atendidos

- Leitura e expansao de matrizes Matrix Market simetricas.
- Conversao para Block ELLPACK com blocos densos.
- Distribuicao de linhas e comunicacao MPI.
- Reducoes globais do Gradiente Conjugado.
- Paralelismo OpenMP no SpMV, produtos escalares e atualizacoes vetoriais.
- Parametros de bloco, tolerancia, threads e maximo de iteracoes.
- Validacao com solucao conhecida e residuo relativo.
- Tres matrizes, quatro block sizes e tres repeticoes.
- Strong scaling MPI e escala hibrida MPI/OpenMP.
- CSVs, estatisticas, graficos, logs e manifestos reproduziveis.

## Limitacoes E Pendencias

- O relatorio principal esta em `report/report.md`; o PDF ainda precisa ser
  gerado para a entrega final.
- A campanha variou processos MPI e threads, mas nao variou explicitamente o
  numero de nos.
- Cada processo constroi uma copia completa da matriz Block ELLPACK; as linhas
  computadas sao distribuidas, mas a matriz nao e particionada fisicamente na
  memoria.
- OpenBLAS esta disponivel e linkado, mas os kernels principais usam operacoes
  C++ paralelas com OpenMP em vez de chamadas diretas `ddot`/`daxpy`.

## Evidencias E Documentacao

- `report/report.md`: relatorio tecnico, tabelas e graficos.
- `docs/diario-de-bordo.md`: historico do desenvolvimento.
- `docs/experiment-evidence-aks.md`: evidencias do AKS.
- `docs/optimization-notes.md`: otimizacoes OpenMP e validacao.
- `docs/queue.md`: fila reproduzivel.
- `AGENT_HANDOFF.md`: requisitos tecnicos originais.

Leia [`AGENT_HANDOFF.md`](AGENT_HANDOFF.md) antes de implementar.
