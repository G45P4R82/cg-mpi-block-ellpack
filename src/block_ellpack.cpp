#include "block_ellpack.hpp"

#include <algorithm>
#include <cmath>
#include <map>
#include <omp.h>
#include <set>
#include <stdexcept>

BlockELL::BlockELL(const SparseMatrix &matrix, int block_size)
    : rows_(matrix.rows), block_size_(block_size), original_nnz_(matrix.entries.size()) {
    if (block_size < 1) throw std::invalid_argument("block-size deve ser positivo");
    block_rows_ = (rows_ + block_size_ - 1) / block_size_;
    std::vector<std::set<int>> columns(block_rows_);
    for (const auto &entry : matrix.entries)
        columns[entry.row / block_size_].insert(entry.col / block_size_);
    for (const auto &set : columns)
        max_block_columns_ = std::max(max_block_columns_, static_cast<int>(set.size()));

    block_columns_.assign(static_cast<std::size_t>(block_rows_) * max_block_columns_, -1);
    values_.assign(static_cast<std::size_t>(block_rows_) * max_block_columns_ * block_size_ * block_size_, 0.0);
    std::map<std::pair<int, int>, int> slot;
    for (int block_row = 0; block_row < block_rows_; ++block_row) {
        int position = 0;
        for (int block_col : columns[block_row]) {
            block_columns_[block_row * max_block_columns_ + position] = block_col;
            slot[{block_row, block_col}] = position++;
        }
    }
    for (const auto &entry : matrix.entries) {
        int block_row = entry.row / block_size_;
        int block_col = entry.col / block_size_;
        int position = slot[{block_row, block_col}];
        int local_row = entry.row % block_size_;
        int local_col = entry.col % block_size_;
        std::size_t offset = (static_cast<std::size_t>(block_row) * max_block_columns_ + position) * block_size_ * block_size_;
        values_[offset + local_row * block_size_ + local_col] = entry.value;
    }
}

void BlockELL::spmv(const std::vector<double> &x, std::vector<double> &y,
                    int first_row, int row_count, int threads) const {
    y.assign(row_count, 0.0);
    const int first_block = first_row / block_size_;
    const int last_block = (first_row + row_count + block_size_ - 1) / block_size_;
    #pragma omp parallel for schedule(static) num_threads(threads)
    for (int block_row = first_block; block_row < last_block; ++block_row) {
        for (int slot = 0; slot < max_block_columns_; ++slot) {
            const int block_col = block_columns_[block_row * max_block_columns_ + slot];
            if (block_col < 0) continue;
            const std::size_t offset = (static_cast<std::size_t>(block_row) * max_block_columns_ + slot) * block_size_ * block_size_;
            for (int local_row = 0; local_row < block_size_; ++local_row) {
                const int row = block_row * block_size_ + local_row;
                if (row < first_row || row >= first_row + row_count || row >= rows_) continue;
                double sum = 0.0;
                for (int local_col = 0; local_col < block_size_; ++local_col) {
                    const int col = block_col * block_size_ + local_col;
                    if (col < rows_) sum += values_[offset + local_row * block_size_ + local_col] * x[col];
                }
                y[row - first_row] += sum;
            }
        }
    }
}

double BlockELL::padding_ratio() const {
    return values_.empty() ? 0.0 : static_cast<double>(padded_values()) / values_.size();
}
