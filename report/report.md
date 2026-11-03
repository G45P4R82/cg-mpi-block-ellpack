# Gradiente Conjugado Distribuido com Block ELLPACK

## Resumo

[Preencher apos a implementacao e os experimentos.]

## Ambiente

[Hardware, sistema, compiladores, MPI, BLAS e OpenMP.]

## Metodologia

[Matrizes, distribuicao, Block ELLPACK, tolerancia e configuracoes.]

## Validacao

[Solucao conhecida, erro e residuo relativo.]

## Resultados

[Tempos de leitura, conversao, solucao, speedup e eficiencia.]

### Primeiro MPIJob validado

O primeiro caso distribuido foi executado com `bcsstk34`, dois processos MPI,
uma thread OpenMP por processo, bloco 8 e tolerancia `1e-8`:

| Metrica | Valor |
|---|---:|
| Leitura | 0.0298194 s |
| Conversao | 0.00491203 s |
| Solucao | 1.41797 s |
| Iteracoes | 736 |
| Residuo relativo | 8.93224e-09 |
| Erro da solucao conhecida | 8.06151e-07 |
| Padding Block ELLPACK | 74.8757% |

O residuo ficou abaixo da tolerancia. O padding elevado mostra que o tamanho
de bloco deve ser avaliado experimentalmente, pois representa memoria ocupada
por zeros.

## Analise

[Comunicacao, memoria, padding, balanceamento e escalabilidade.]

## Conclusao

[Conclusoes e trabalho futuro.]
