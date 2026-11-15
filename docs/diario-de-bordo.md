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
