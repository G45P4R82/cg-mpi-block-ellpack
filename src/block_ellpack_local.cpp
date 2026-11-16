#include "block_ellpack_local.hpp"

#include <algorithm>
#include <map>
#include <omp.h>
#include <set>
#include <stdexcept>

BlockELLLocal::BlockELLLocal(const SparseMatrix &local_entries,
                             int block_size,
                             int first_row,
                             int row_count)
    : block_size_(block_size),
      first_row_(first_row),
      row_count_(row_count),
      original_nnz_(local_entries.entries.size()) {
    if (block_size < 1) throw std::invalid_argument("block-size deve ser positivo");
    if (row_count < 0 || first_row < 0)
        throw std::invalid_argument("intervalo local invalido");
    first_block_row_ = first_row_ / block_size_;
    const int last_row_exclusive = first_row_ + row_count_;
    const int last_block_row_exclusive =
        (last_row_exclusive + block_size_ - 1) / block_size_;
    block_rows_ = last_block_row_exclusive - first_block_row_;
    if (block_rows_ < 0) block_rows_ = 0;

    std::vector<std::set<int>> columns(block_rows_);
    for (const auto &entry : local_entries.entries) {
        const int block_row = entry.row / block_size_ - first_block_row_;
        if (block_row < 0 || block_row >= block_rows_) continue;
        columns[block_row].insert(entry.col / block_size_);
    }

    for (const auto &set : columns)
        max_block_columns_ = std::max(max_block_columns_,
                                      static_cast<int>(set.size()));

    const std::size_t row_capacity =
        static_cast<std::size_t>(block_rows_) * max_block_columns_;
    block_columns_.assign(row_capacity, -1);
    values_.assign(row_capacity * block_size_ * block_size_, 0.0);

    std::map<std::pair<int, int>, int> slot;
    std::set<int> referenced_block_cols;
    for (int block_row = 0; block_row < block_rows_; ++block_row) {
        int position = 0;
        for (int block_col : columns[block_row]) {
            block_columns_[block_row * max_block_columns_ + position] = block_col;
            slot[{block_row, block_col}] = position++;
            referenced_block_cols.insert(block_col);
        }
    }

    for (const auto &entry : local_entries.entries) {
        const int block_row = entry.row / block_size_ - first_block_row_;
        if (block_row < 0 || block_row >= block_rows_) continue;
        const int block_col = entry.col / block_size_;
        const int position = slot[{block_row, block_col}];
        const int local_row = entry.row % block_size_;
        const int local_col = entry.col % block_size_;
        const std::size_t offset =
            (static_cast<std::size_t>(block_row) * max_block_columns_ + position)
            * block_size_ * block_size_;
        values_[offset + local_row * block_size_ + local_col] = entry.value;
    }

    // Expande os indices de coluna de bloco em indices globais (cada bloco
    // cobre block_size colunas consecutivas). Alguns indices podem exceder
    // a dimensao global quando o ultimo bloco inclui padding; isso sera
    // filtrado pelo CG que conhece o tamanho global.
    referenced_columns_.clear();
    referenced_columns_.reserve(referenced_block_cols.size() * block_size_);
    for (int block_col : referenced_block_cols) {
        const int start = block_col * block_size_;
        for (int offset = 0; offset < block_size_; ++offset) {
            referenced_columns_.push_back(start + offset);
        }
    }
    std::sort(referenced_columns_.begin(), referenced_columns_.end());
    referenced_columns_.erase(
        std::unique(referenced_columns_.begin(), referenced_columns_.end()),
        referenced_columns_.end());
}

void BlockELLLocal::spmv(const std::vector<double> &x,
                         std::vector<double> &y,
                         int threads) const {
    y.assign(row_count_, 0.0);
    #pragma omp parallel for schedule(static) num_threads(threads)
    for (int block_row = 0; block_row < block_rows_; ++block_row) {
        for (int slot_index = 0; slot_index < max_block_columns_; ++slot_index) {
            const int block_col =
                block_columns_[block_row * max_block_columns_ + slot_index];
            if (block_col < 0) continue;
            const std::size_t offset =
                (static_cast<std::size_t>(block_row) * max_block_columns_ + slot_index)
                * block_size_ * block_size_;
            for (int local_row = 0; local_row < block_size_; ++local_row) {
                const int global_row =
                    (block_row + first_block_row_) * block_size_ + local_row;
                if (global_row < first_row_ ||
                    global_row >= first_row_ + row_count_) continue;
                double sum = 0.0;
                for (int local_col = 0; local_col < block_size_; ++local_col) {
                    const int col = block_col * block_size_ + local_col;
                    if (col < 0 || col >= static_cast<int>(x.size())) continue;
                    sum += values_[offset + local_row * block_size_ + local_col]
                         * x[col];
                }
                y[global_row - first_row_] += sum;
            }
        }
    }
}

double BlockELLLocal::padding_ratio() const {
    if (values_.empty()) return 0.0;
    return static_cast<double>(padded_values()) /
           static_cast<double>(values_.size());
}

std::size_t BlockELLLocal::memory_bytes() const {
    return values_.size() * sizeof(double) +
           block_columns_.size() * sizeof(int) +
           referenced_columns_.size() * sizeof(int);
}
