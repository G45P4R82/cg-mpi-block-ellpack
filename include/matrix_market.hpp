#pragma once

#include <cstddef>
#include <string>
#include <vector>

struct Triplet {
    int row;
    int col;
    double value;
};

struct SparseMatrix {
    int rows = 0;
    int cols = 0;
    std::vector<Triplet> entries;
};

SparseMatrix read_matrix_market(const std::string &path);

// Le o arquivo Matrix Market mas armazena apenas as triplas cuja linha
// (depois da expansao simetrica) pertence ao intervalo [first_row,
// first_row + row_count). Cada rank MPI pode chamar a funcao em paralelo
// com um intervalo proprio para evitar replicar a matriz na memoria.
// rows e cols do SparseMatrix retornado sao os valores globais do arquivo.
SparseMatrix read_matrix_market_local(const std::string &path,
                                      int first_row,
                                      int row_count);
