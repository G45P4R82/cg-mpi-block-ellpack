# Validacao

Para cada matriz, construir uma solucao conhecida `x_true` e calcular
`b=A*x_true`. A solucao do CG deve ser comparada com `x_true` usando norma
relativa. Tambem deve ser calculado explicitamente:

```text
relative_residual = ||b - A*x||_2 / ||b||_2
```

O teste deve confirmar que a matriz expandida a partir do Matrix Market continua
simetrica e que a diagonal nao foi duplicada ao expandir entradas triangulares.
