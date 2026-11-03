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
