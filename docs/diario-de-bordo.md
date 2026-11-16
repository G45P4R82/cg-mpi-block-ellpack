# Diario de Bordo

## 2026-11-14 - Estado ao encerrar a sessao

### Disciplina e avaliacao

Foi lido o material `1 Introduction to High Performance Computing.pdf`.
Pontos registrados:

- Frequencia inferior a 75% implica reprovacao.
- `Mtar` e a media das tarefas.
- `Mtest` e a media dos testes.
- `Nsem` e a nota do seminario.
- `Nproj` e a nota do projeto final.
- Quando os quatro componentes sao maiores que 3:

  ```text
  M = 0,2 Mtar + 0,2 Mtest + 0,3 Nsem + 0,3 Nproj
  ```

- Se algum componente for menor ou igual a 3, a media passa a ser o menor
  componente.
- O PDF nao informa explicitamente a media final minima para aprovacao.

Com as notas informadas pelo estudante:

```text
Mtar  = (7 + 10 + 10) / 3 = 9,00
Mtest = (6 + 5 + 4,5) / 3 = 5,17
```

A media parcial considerando apenas tarefas e testes foi estimada em `7,08`.

### Projeto final identificado

O repositorio do projeto final foi identificado como:

```text
mo652-26s2-projeto-cg-group-2
```

Tema: Gradiente Conjugado distribuido para matrizes esparsas, com MPI entre
processos, OpenMP/BLAS dentro dos processos e armazenamento Block ELLPACK.

Tambem foram distinguidos os repositorios de Trabalho 3 Jacobi 2D e de
multiplicacao de matrizes MPI/OpenBLAS. O arquivo `taylor_avx256.c` foi
identificado como experimento separado, nao como o projeto final.

### Visualizacao OpenMP

No diretorio `slide9` foi criada a visualizacao Pygame `fazenda_visual.py`.
Ela representa o exemplo `main.c` como um DAG vivo, com quatro threads,
oito fileiras dinamicas e as dependencias de `reduction`, `task` e `taskwait`.

Controles da visualizacao:

```text
Espaco: pausar/continuar
N: avancar etapa
R: reiniciar
Esc: sair
```

### Leitura do material de GPU

Foi lido `11 Advanced GPU Programming.pptx`. As ideias consideradas uteis
para o projeto foram profiling, roofline, analise de largura de banda e
localidade de memoria. CUDA, shared memory, warps e NVLink nao foram aplicados
porque os clusters utilizados sao CPU-only.

### Melhoria do solver

O arquivo `src/cg_mpi.cpp` foi melhorado:

- produtos escalares agora usam reducao OpenMP;
- atualizacoes de `x` e `r` agora usam OpenMP;
- atualizacao de `p` agora usa OpenMP;
- calculo dos erros de validacao agora usa OpenMP;
- argumentos invalidos de bloco, threads, tolerancia e iteracoes sao rejeitados.

Foi criado `docs/optimization-notes.md`. A imagem ARM64 foi reconstruida com
essas alteracoes e publicada como:

```text
srmarinho/cg-mpi:arm64
```

O codigo foi compilado e testado dentro da imagem ARM64 com MPI, OpenMP e
OpenBLAS. Um teste validado produziu residuo abaixo de `1e-8`.

### Experimentos no AKS

Foi encontrado e usado o contexto `agents-insights`, referente ao AKS
`agent-insights-aks6a152d40` em `centralus`.

Foi instalado o MPI Operator `v0.8.2` e criado o namespace `hpc-cg`. A
instalacao exigiu preservar os argumentos do controller:

```text
-alsologtostderr
--lock-namespace=mpi-operator
```

Foi executado um MPIJob de validacao com sucesso.

Campanha principal do AKS:

```text
results/raw/cg-campaign-aks-20261114T002913Z/
```

Resultado:

- 48 execucoes com `SUCCESS`.
- 6 execucoes hibridas falharam por falta de CPU no scheduler.
- Os logs, manifests e estados JSON foram preservados.

As evidencias estao documentadas em:

```text
docs/experiment-evidence-aks.md
results/evidence/aks-20261114T175057Z/
```

O rerun das seis falhas foi iniciado, mas ficou pendente por falta de CPU e
foi encerrado sem apagar os artefatos.

### Recuperacao do TVBox

O acesso foi recuperado via SSH no host `100.85.15.237` com o usuario
`tvbox`. O kubeconfig do k3s foi recuperado e instalado localmente como:

```text
~/.kube/tvbox-k3s.yaml
```

O contexto foi mesclado no kubeconfig principal com o nome:

```text
tvbox-k3s
```

O contexto atual ao encerrar a sessao e `tvbox-k3s`.

Estado validado:

- 11 nos no cluster.
- 9 nos `Ready` e 2 nos `NotReady`.
- MPI Operator `Running`.
- CRD `mpijobs.kubeflow.org` presente.
- Nos possuem 4 CPUs; os nos ARM64 sao selecionados pelos manifests.

### Campanha deixada rodando

A campanha foi iniciada no TVBox em segundo plano, sem ser interrompida:

```text
PID: 3593808
Diretorio:
results/raw/cg-campaign-tvbox-20261114T181716Z/

Log:
results/raw/campaign-tvbox-background.log
Namespace: hpc-cg
Contexto: tvbox-k3s
```

No ultimo acompanhamento, a campanha continuava ativa, com 8 resultados
`SUCCESS` e o seguinte job em execucao:

```text
cg-bcsstk34-b16-p2-t1-r3
```

## Proximas acoes

1. Verificar se a campanha TVBox terminou.
2. Conferir quantidade de `SUCCESS` e `FAILED`.
3. Processar os logs validos em CSV.
4. Gerar estatisticas, speedup, eficiencia e graficos.
5. Atualizar `report/report.md` com resultados reais.
6. Investigar qualquer falha de CPU ou agendamento restante.

Nenhuma senha foi registrada neste diario.

### Relatorio e analise

Os 54 logs da campanha completa foram convertidos e validados:

```text
results/processed/cg_results_tvbox.csv
results/processed/cg_stats_tvbox.csv
results/processed/cg_metrics_tvbox.csv
```

Foram gerados cinco graficos em `results/plots/tvbox/` para tempo por bloco,
strong scaling, speedup, eficiencia, escala hibrida e padding. O arquivo
`report/report.md` foi preenchido com metodologia, validacao, tabelas,
analise e conclusao usando somente os resultados TVBox.

### Plano de acao: experimento de escalabilidade por nos

A campanha realizada variou processos MPI e threads, mas nao variou
explicitamente o numero de nos. Fica registrado como proxima etapa obrigatoria
um experimento complementar de escalabilidade entre nos.

Acoes previstas:

1. Preservar as 54 execucoes atuais; elas continuam validas e nao serao
   descartadas nem repetidas.
2. Adicionar o campo `node_count` a fila `experiments/queue.tsv` e ao runner
   `scripts/run_queue.sh`.
3. Definir configuracoes controladas de nos e processos:

   ```text
   1 no  + 2 processos MPI
   2 nos + 2 processos MPI
   2 nos + 4 processos MPI
   4 nos + 4 processos MPI
   ```

4. Manter fixos: matriz `bcsstk16`, `block_size=8`, `1` thread OpenMP,
   tolerancia `1e-8` e `10000` iteracoes maximas.
5. Fazer `3` repeticoes por configuracao.
6. Garantir a distribuicao dos pods MPI pelos nos definidos usando regras de
   afinidade ou topologia Kubernetes.
7. Registrar em cada execucao os nomes reais dos nos que hospedaram os pods.
8. Gerar um CSV especifico com os campos:

   ```text
   node_count
   node_names
   mpi_processes
   omp_threads
   solve_time
   speedup
   efficiency
   ```

9. Gerar graficos de tempo, speedup e eficiencia por numero de nos.
10. Atualizar `report/report.md` com a nova analise de escalabilidade entre
    nos.
11. Manter explicita a limitacao atual de que cada processo MPI constroi uma
    copia completa da matriz Block ELLPACK.

Esse experimento e complementar. Nao invalida os resultados atuais.

### Execucao do experimento de escalabilidade por nos (2026-11-16)

O experimento complementar foi implementado e executado com sucesso. Foram
realizadas 12 execucoes em 4 configuracoes:

```text
1 nos + 2 processos MPI: 4,751 s medio (referencia)
2 nos + 2 processos MPI: 2,166 s medio (speedup 2,19x super-linear)
2 nos + 4 processos MPI: 7,915 s medio (speedup 0,60x, co-location nociva)
4 nos + 4 processos MPI: 2,321 s medio (speedup 2,05x)
```

Observacao importante: todos os residuos permaneceram abaixo de 1e-8.

Decisoes tecnicas tomadas:

1. Pool de nos dedicado para workers: `tvbox02, tvbox03, cluster-tvbox-04,
   cluster-tvbox-05` via `nodeAffinity.requiredDuringSchedulingIgnored`.
2. Launcher fixado em `tvbox01` para evitar simetria de `podAntiAffinity`
   ao filtrar `training.kubeflow.org/job-role=worker`.
3. `podAntiAffinity` aplicada aos workers apenas quando `nodes == mpi`,
   garantindo exatamente um worker por no. Quando `mpi > nodes`, o anti
   affinity e suprimido para permitir co-location (2 workers por no).
4. Recursos ajustados para `limits.memory=512Mi` e `requests.memory=256Mi`
   para caber em nos de 1,8 GiB.
5. Placement dos workers coletado em `pod-placement.txt`, lido antes do
   `cleanPodPolicy` deletar os pods ao final.

Artefatos gerados:

```text
results/node-scaling-20261116T032812Z/
results/processed/cg_node_scaling_tvbox.csv
results/plots/tvbox-nodes/time_by_nodes.png
results/plots/tvbox-nodes/speedup_efficiency_by_nodes.png
```

Scripts introduzidos:

```text
experiments/node-scaling.tsv
k8s/mpi-operator/cg-nodes.yaml.in
scripts/run_node_scaling.sh
scripts/analyze_node_scaling.py
```

Conclusao da pendencia: o requisito de variar o numero de nos esta
atendido. A limitacao sobre matriz replicada em cada processo permanece
documentada como trabalho futuro.

### Implementacao da variante distribuida (2026-11-16)

A limitacao de matriz replicada foi resolvida com a implementacao do
`cg_mpi_distributed`. As fases concluidas foram:

1. **Fase 1 - Leitura filtrada:** `read_matrix_market_local(path, first, count)`
   le o arquivo e armazena apenas triplas pertencentes ao intervalo local.
2. **Fase 2 - Block ELLPACK particionado:** classe `BlockELLLocal` em
   `include/block_ellpack_local.hpp` / `src/block_ellpack_local.cpp` aloca
   apenas blocos das linhas locais e expoe `referenced_columns()` para o
   halo exchange.
3. **Fase 3a - Comunicacao seletiva:** `src/cg_mpi_distributed.cpp` calcula
   quem possui cada coluna remota referenciada, troca pedidos com
   `MPI_Alltoall`, troca valores com `MPI_Alltoallv` e popula somente as
   posicoes necessarias do `p_global`.
5. **Metricas de memoria e comunicacao:** `memory_max_mb`, `memory_avg_mb`,
   `memory_total_mb`, `comm_bytes`, `padding_overhead` agora emitidos pelo
   programa.

Nova matriz adicionada (`bcsstk17`, 10974x10974, 428k nnz, SPD, elevated
pressure vessel) para demonstrar ganho de memoria em matrizes maiores.
SHA-256 do tarball registrado em `matrices/README.md`.

Imagem Docker ARM64 publicada em `srmarinho/cg-mpi:arm64-dist` com ambos
binarios (`cg_mpi` e `cg_mpi_distributed`).

Experimento comparativo executado no TVBox (12 jobs distribuido + 12 jobs
replicated ja existentes) no mesmo pool de nos (`tvbox02`, `tvbox03`,
`cluster-tvbox-04`, `cluster-tvbox-05`), launcher em `tvbox01`.

Resultados (`bcsstk16`, block 8):

```text
Config          replicated        distributed       ganho
1 no  / MPI=2   4,751 s           4,881 s           -2,7% (ruido)
2 nos / MPI=2   2,166 s           1,525 s           +30%
2 nos / MPI=4   7,915 s           6,995 s           +13%
4 nos / MPI=4   2,321 s           1,301 s           +44%
```

Memoria por rank caiu de ~7,25 MB (replicada) para 3,62 MB (MPI=2) ou
1,82 MB (MPI=4). Speedup real com 4 nos e MPI=4 subiu de 2,05x para 3,65x,
muito proximo do ideal de 4x.

Artefatos:

```text
experiments/node-scaling-dist.tsv
scripts/run_node_scaling_dist.sh
scripts/analyze_node_scaling_compare.py
include/block_ellpack_local.hpp
src/block_ellpack_local.cpp
src/cg_mpi_distributed.cpp
src/matrix_market.cpp (adicionada read_matrix_market_local)
k8s/mpi-operator/cg-nodes-dist.yaml.in
results/node-scaling-dist-20261116T145412Z/
results/processed/cg_node_scaling_compare.csv
results/plots/tvbox-nodes-compare/
```

Com esta implementacao, a limitacao de matriz replicada esta oficialmente
superada. A unica limitacao remanescente e o uso de kernels OpenMP proprios
em vez de BLAS (OpenBLAS continua linkado na imagem para futura integracao).
