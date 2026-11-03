# Primeiro MPIJob CG

## Configuracao

```text
matriz: bcsstk34
processos MPI: 2
threads OpenMP por processo: 1
block-size: 8
tolerancia: 1e-8
max-iters: 10000
plataforma: k3s ARM64 via MPI Operator
```

## Resultado

```text
rows=588
nnz=21418
read_time_s=0.0298194
conversion_time_s=0.00491203
solve_time_s=1.41797
iterations=736
relative_residual=8.93224e-09
solution_error=8.06151e-07
padding_overhead=0.748757
```

O residuo ficou abaixo da tolerancia `1e-8`. O padding do Block ELLPACK foi
aproximadamente 74,9% nesta configuracao, um ponto importante para comparar
com outros tamanhos de bloco.

Log completo: `results/raw/cg-bcsstk34-mpi2.log`.
