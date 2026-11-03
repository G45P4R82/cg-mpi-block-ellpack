# Instrucoes para a IA executora

Implemente, teste, execute e documente o projeto completo. O repositorio ja
possui as matrizes em `matrices/`; nao baixe novamente os arquivos durante os
Jobs.

## Implementacao obrigatoria

Criar:

```text
src/matrix_market.cpp
src/block_ellpack.cpp
src/cg_mpi.cpp
include/matrix_market.hpp
include/block_ellpack.hpp
include/cg.hpp
```

O programa deve:

- ler Matrix Market coordinate real symmetric;
- expandir corretamente a parte triangular, sem duplicar a diagonal;
- converter para Block ELLPACK;
- permitir `--block-size`, `--tol` e `--max-iters`;
- distribuir linhas entre processos MPI;
- realizar SpMV distribuido;
- realizar `MPI_Allreduce` para produtos escalares;
- usar OpenMP e/ou BLAS dentro do processo;
- informar tempo de leitura, conversao e solucao;
- informar iteracoes e residuo relativo final.

## CG

Com `x0=0`:

```text
r = b - A*x
p = r
rho = dot(r,r)

repeat:
    q = A*p
    alpha = rho / dot(p,q)
    x = x + alpha*p
    r = r - alpha*q
    rho_new = dot(r,r)
    stop if sqrt(rho_new)/||b|| <= tol
    beta = rho_new/rho
    p = r + beta*p
    rho = rho_new
```

Use uma matriz SPD e uma solucao conhecida `x_true`, por exemplo um vetor de
uns, para construir `b=A*x_true`. Compare `x` com `x_true` e calcule tambem o
residuo explicito `||b-Ax||/||b||`.

## Block ELLPACK

Documente precisamente a representacao escolhida. Para cada bloco de linhas,
armazenar um numero fixo de entradas/colunas, preencher padding com zeros e
medir:

- bytes armazenados;
- nao zeros originais;
- zeros de padding;
- percentual de overhead;
- tamanho do bloco.

Testar pelo menos:

```text
block-size = 4, 8, 16, 32
```

## MPI e OpenMP

Implementar inicialmente uma distribuicao por blocos de linhas. A versao
baseline pode usar `MPI_Allgatherv` para disponibilizar o vetor global; uma
versao otimizada deve trocar apenas os elementos remotos quando viavel.

Registrar o custo de:

- comunicacao do vetor;
- SpMV local;
- reducoes globais;
- atualizacao dos vetores.

Usar OpenMP com `schedule(static)` e registrar `OMP_NUM_THREADS`,
`OMP_PROC_BIND` e `OMP_PLACES`.

## Experimentos

Para cada matriz:

- processos MPI: 1, 2, 4, 8, conforme os recursos;
- threads por processo: 1, 2, 4;
- block-size: 4, 8, 16, 32;
- pelo menos tres repeticoes;
- mesma tolerancia e mesmo maximo de iteracoes.

Medir escalabilidade forte mantendo a matriz fixa e comparar tamanhos de
problema entre as tres matrizes.

## Saida obrigatoria

Cada execucao deve emitir formato estruturado contendo:

```text
matrix=...
rows=...
nnz=...
block_size=...
mpi_processes=...
omp_threads=...
read_time_s=...
conversion_time_s=...
solve_time_s=...
iterations=...
relative_residual=...
solution_error=...
padding_overhead=...
```

Nao publicar nomes de hosts, caminhos privados, credenciais ou configuracoes
internas do cluster.
