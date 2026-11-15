# Otimizacoes do Solver

## Paralelismo OpenMP

O solver agora usa o mesmo valor de `--threads` nas operacoes vetoriais do
Gradiente Conjugado:

- produtos escalares com `reduction(+:result)`;
- atualizacao de `x` e `r` depois do calculo de `alpha`;
- atualizacao de `p` depois do calculo de `beta`;
- calculo dos erros de residuo e da solucao conhecida.

O `SpMV` em Block ELLPACK ja usava `schedule(static)`. Com a mudanca, o
calculo nao fica limitado ao `SpMV`: as reducoes locais e as operacoes SAXPY
dos vetores tambem podem utilizar os nucleos disponiveis.

## Validacao da mudanca

O codigo foi compilado com `mpicxx`, OpenMP e OpenBLAS dentro da imagem ARM64
do projeto. Um teste com `bcsstk34`, dois processos MPI, bloco 8 e duas
threads por processo terminou com:

```text
iterations=734
relative_residual=7.51768e-09
solution_error=8.04024e-07
padding_overhead=0.748757
```

O residuo ficou abaixo da tolerancia `1e-8`. Os tempos observados em um teste
local no container foram `0.879517 s` com uma thread e `0.493918 s` com duas
threads; esses valores nao substituem a medicao oficial no cluster.

## Proximos gargalos

O maior custo estrutural ainda e o `MPI_Allgatherv` a cada iteracao, seguido
pelos `MPI_Allreduce`. O padding do Block ELLPACK tambem pode ser alto. Essas
partes devem ser medidas antes de trocar o formato ou introduzir comunicacao
nao bloqueante.
