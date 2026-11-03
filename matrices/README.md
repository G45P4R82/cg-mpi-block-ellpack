# Matrizes do Experimento

As matrizes foram baixadas uma única vez do arquivo histórico da UF Sparse
Matrix Collection. Os arquivos foram extraídos e mantidos no repositório para
evitar novos downloads durante os Jobs PBS.

| Matriz | Dimensão | Não zeros | Origem |
|---|---:|---:|---|
| `bcsstk34` | 588 x 588 | 21.418 | Boeing |
| `bcsstk14` | 1.806 x 1.806 | 63.454 | HB |
| `bcsstk16` | 4.884 x 4.884 | 290.378 | HB |

Todas possuem cabeçalho Matrix Market `real symmetric`. A seleção original da
SuiteSparse foi feita com os filtros `Symmetric=Yes` e
`Positive Definite=Yes`. A positividade deve ser confirmada novamente pelo
parser/validador do projeto antes dos experimentos definitivos.

## Fontes

```text
https://www.cise.ufl.edu/research/sparse/MM/Boeing/bcsstk34.tar.gz
https://www.cise.ufl.edu/research/sparse/MM/HB/bcsstk14.tar.gz
https://www.cise.ufl.edu/research/sparse/MM/HB/bcsstk16.tar.gz
```

## SHA-256 dos tarballs

```text
bcsstk34.tar.gz  a2c0df0b6ee2db8abeda3de7bba240ae0a52c49460188bbd2afba8c6d928f81b
bcsstk14.tar.gz  c991b4801adde149520d18969cf57dc2ed4c1ded7b147f6631f6c9edb2ec84ba
bcsstk16.tar.gz  576aa9abde8d766824bc21524284884b2110bd3a384d8f5a95df06a6c60cd3a
```
