# Plano de Experimentos

## Matrizes

Usar `bcsstk34`, `bcsstk14` e `bcsstk16`, preservadas em `matrices/`.
Registrar dimensao, nao zeros, grupo e hash.

## Configuracoes

```text
MPI: 1, 2, 4, 8 processos quando disponivel
OpenMP: 1, 2, 4 threads por processo
Block ELLPACK: 4, 8, 16, 32
tolerancia: 1e-8 ou valor justificado
max-iters: valor fixo documentado
repeticoes: >= 3
```

## Metricas

- leitura;
- conversao;
- memoria e padding;
- solucao;
- iteracoes;
- residuo relativo;
- erro em relacao a `x_true`;
- speedup;
- eficiencia.

## Comunicacao

Registrar o tempo de `MPI_Allgatherv`/halo exchange e `MPI_Allreduce`. Explicar
o particionamento de linhas e o balanceamento de carga.
