# Evidencias dos Experimentos no AKS

## Cluster

- Contexto: `agents-insights`
- Cluster: `agent-insights-aks6a152d40`
- Regiao: `centralus`
- Kubernetes: `v1.36.4`
- Nos: 6 nos ARM64, cada um com 2 CPUs e aproximadamente 8 GiB de memoria
- Namespace usado: `hpc-cg`
- MPI Operator: `v0.8.2`

O contexto global `kubectl` nao foi alterado; os comandos foram executados com
`--context agents-insights`.

## Imagem e Codigo

A imagem ARM64 foi reconstruida depois das melhorias OpenMP no solver e enviada
para:

```text
srmarinho/cg-mpi:arm64
```

O teste de validacao executado no AKS com `bcsstk34` terminou com:

```text
block_size=4
mpi_processes=2
omp_threads=1
solve_time_s=0.464861
iterations=737
relative_residual=8.37336e-09
solution_error=7.95949e-07
padding_overhead=0.696457
```

## Campanha Principal

Diretorio dos manifestos e logs:

```text
results/raw/cg-campaign-aks-20261114T002913Z/
```

Foram executadas as seguintes familias:

- Tres matrizes: `bcsstk34`, `bcsstk14` e `bcsstk16`.
- Block sizes: `4`, `8`, `16` e `32`.
- Tres repeticoes por configuracao.
- Escala MPI: `1`, `2` e `4` processos.
- Escala hibrida: `2` processos MPI com `1`, `2` e `4` threads OpenMP.

Resultado registrado em `results/raw/campaign-aks-background.log`:

- 48 execucoes concluidas com `SUCCESS`.
- 6 execucoes hibridas falharam por `Insufficient cpu` no scheduler do AKS.
- As 6 falhas foram `2` processos MPI com `2` ou `4` threads OpenMP.

Os logs individuais, manifests YAML e arquivos de estado das falhas foram
preservados no diretorio da campanha.

## Rerun Interrompido

O rerun das seis falhas foi iniciado no AKS, mas ficou pendente porque os dois
workers solicitavam 2 CPUs cada e todos os nos estavam sem CPU disponivel.
Essa evidencia esta em:

```text
results/raw/cg-rerun-aks-20261114T175057Z/
```

O rerun nao produziu resultados validos e nao deve ser misturado com a
campanha principal.
