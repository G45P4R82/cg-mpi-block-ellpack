#pragma once

#include "matrix_market.hpp"

#include <cstddef>
#include <vector>

// Variante distribuida do Block ELLPACK. Cada rank MPI armazena apenas as
// linhas locais definidas por [first_row, first_row + row_count). Para
// executar o SpMV local, cada rank precisa dos elementos do vetor global
// cujos indices de coluna aparecem nos blocos locais; esses indices sao
// expostos por `remote_columns()` para que o algoritmo de CG monte um
// `p_view` consistente antes de chamar `spmv`.
class BlockELLLocal {
public:
    BlockELLLocal() = default;
    BlockELLLocal(const SparseMatrix &local_entries,
                  int block_size,
                  int first_row,
                  int row_count);

    // Executa y = A_local * x, onde x deve conter os valores de todas as
    // colunas globais referenciadas pelos blocos locais. Se o chamador
    // preferir trabalhar com um vetor compactado, use
    // `global_column_index_for(local_index)` para montar `x`.
    void spmv(const std::vector<double> &x,
              std::vector<double> &y,
              int threads) const;

    int block_size() const { return block_size_; }
    int first_row() const { return first_row_; }
    int row_count() const { return row_count_; }
    int block_rows() const { return block_rows_; }
    int max_block_columns() const { return max_block_columns_; }
    std::size_t stored_values() const { return values_.size(); }
    std::size_t original_nnz() const { return original_nnz_; }
    std::size_t padded_values() const {
        return values_.size() > original_nnz_ ? values_.size() - original_nnz_ : 0;
    }
    double padding_ratio() const;
    std::size_t memory_bytes() const;

    // Indices globais das colunas efetivamente referenciadas pelos blocos
    // locais. Ordenados de forma crescente e usados pelo CG para montar a
    // comunicacao seletiva.
    const std::vector<int> &referenced_columns() const { return referenced_columns_; }

private:
    int block_size_ = 1;
    int first_row_ = 0;
    int row_count_ = 0;
    int block_rows_ = 0;
    int max_block_columns_ = 0;
    int first_block_row_ = 0;
    std::vector<int> block_columns_;
    std::vector<double> values_;
    std::vector<int> referenced_columns_;
    std::size_t original_nnz_ = 0;
};
