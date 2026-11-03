#pragma once

#include "matrix_market.hpp"

#include <cstddef>
#include <vector>

class BlockELL {
public:
    BlockELL() = default;
    BlockELL(const SparseMatrix &matrix, int block_size);

    void spmv(const std::vector<double> &x, std::vector<double> &y,
              int first_row, int row_count, int threads) const;

    int rows() const { return rows_; }
    int block_size() const { return block_size_; }
    std::size_t stored_values() const { return values_.size(); }
    std::size_t original_nnz() const { return original_nnz_; }
    std::size_t padded_values() const { return values_.size() - original_nnz_; }
    double padding_ratio() const;

private:
    int rows_ = 0;
    int block_size_ = 1;
    int block_rows_ = 0;
    int max_block_columns_ = 0;
    std::vector<int> block_columns_;
    std::vector<double> values_;
    std::size_t original_nnz_ = 0;
};
