#pragma once

#include "block_ellpack.hpp"

#include <vector>

struct CGResult {
    int iterations = 0;
    double relative_residual = 0.0;
    double solution_error = 0.0;
    double solve_time_s = 0.0;
};

CGResult conjugate_gradient(const BlockELL &matrix, const std::vector<double> &b,
                            std::vector<double> &x, double tolerance,
                            int max_iterations, int first_row, int local_rows,
                            int global_rows, int threads);
