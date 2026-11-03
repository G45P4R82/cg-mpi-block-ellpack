#include "cg.hpp"
#include "matrix_market.hpp"

#include <mpi.h>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>

struct Args {
    std::string matrix;
    int block_size = 8;
    int threads = 1;
    int max_iterations = 10000;
    double tolerance = 1e-8;
};

static Args parse_args(int argc, char **argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        std::string option(argv[i]);
        if (i + 1 >= argc) throw std::runtime_error("argumento sem valor: " + option);
        if (option == "--matrix") args.matrix = argv[++i];
        else if (option == "--block-size") args.block_size = std::stoi(argv[++i]);
        else if (option == "--threads") args.threads = std::stoi(argv[++i]);
        else if (option == "--max-iters") args.max_iterations = std::stoi(argv[++i]);
        else if (option == "--tol") args.tolerance = std::stod(argv[++i]);
        else throw std::runtime_error("opcao desconhecida: " + option);
    }
    if (args.matrix.empty()) throw std::runtime_error("--matrix e obrigatorio");
    return args;
}

static double dot(const std::vector<double> &a, const std::vector<double> &b) {
    double result = 0.0;
    for (std::size_t i = 0; i < a.size(); ++i) result += a[i] * b[i];
    return result;
}

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
    int rank = 0, processes = 1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &processes);
    try {
        const Args args = parse_args(argc, argv);
        const auto read_start = std::chrono::steady_clock::now();
        SparseMatrix sparse = read_matrix_market(args.matrix);
        const auto read_end = std::chrono::steady_clock::now();
        const auto convert_start = std::chrono::steady_clock::now();
        BlockELL matrix(sparse, args.block_size);
        const auto convert_end = std::chrono::steady_clock::now();
        const int n = sparse.rows;
        const int first = (n * rank) / processes;
        const int last = (n * (rank + 1)) / processes;
        const int local_rows = last - first;
        std::vector<int> counts(processes), displacements(processes);
        for (int p = 0; p < processes; ++p) {
            counts[p] = (n * (p + 1)) / processes - (n * p) / processes;
            displacements[p] = (n * p) / processes;
        }
        std::vector<double> x_local(local_rows, 0.0), p_local, r_local, b_local;
        std::vector<double> x_global(n, 1.0);
        matrix.spmv(x_global, b_local, first, local_rows, args.threads);
        r_local = b_local;
        p_local = r_local;
        double local_rho = dot(r_local, r_local), rho = 0.0;
        MPI_Allreduce(&local_rho, &rho, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
        double norm_b = std::sqrt(rho);
        int iterations = 0;
        const auto solve_start = std::chrono::steady_clock::now();
        std::vector<double> p_global(n), q_local;
        double relative_residual = 1.0;
        for (; iterations < args.max_iterations && norm_b > 0.0; ++iterations) {
            MPI_Allgatherv(p_local.data(), local_rows, MPI_DOUBLE, p_global.data(), counts.data(), displacements.data(), MPI_DOUBLE, MPI_COMM_WORLD);
            matrix.spmv(p_global, q_local, first, local_rows, args.threads);
            double local_pq = dot(p_local, q_local), pq = 0.0;
            MPI_Allreduce(&local_pq, &pq, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
            if (!(pq > 0.0)) throw std::runtime_error("p^T A p nao positivo; matriz pode nao ser SPD");
            const double alpha = rho / pq;
            for (int i = 0; i < local_rows; ++i) {
                x_local[i] += alpha * p_local[i];
                r_local[i] -= alpha * q_local[i];
            }
            double local_new_rho = dot(r_local, r_local), new_rho = 0.0;
            MPI_Allreduce(&local_new_rho, &new_rho, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
            relative_residual = std::sqrt(new_rho) / norm_b;
            if (relative_residual <= args.tolerance) { ++iterations; break; }
            const double beta = new_rho / rho;
            for (int i = 0; i < local_rows; ++i) p_local[i] = r_local[i] + beta * p_local[i];
            rho = new_rho;
        }
        const auto solve_end = std::chrono::steady_clock::now();
        std::vector<double> x_check(n);
        MPI_Allgatherv(x_local.data(), local_rows, MPI_DOUBLE, x_check.data(), counts.data(), displacements.data(), MPI_DOUBLE, MPI_COMM_WORLD);
        std::vector<double> ax_local;
        matrix.spmv(x_check, ax_local, first, local_rows, args.threads);
        double local_residual_error = 0.0, local_solution_error = 0.0;
        for (int i = 0; i < local_rows; ++i) {
            const double residual = ax_local[i] - b_local[i];
            local_residual_error += residual * residual;
            const double solution_error = x_local[i] - 1.0;
            local_solution_error += solution_error * solution_error;
        }
        double residual_error = 0.0, solution_error = 0.0;
        MPI_Allreduce(&local_residual_error, &residual_error, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
        MPI_Allreduce(&local_solution_error, &solution_error, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
        if (rank == 0) {
            const double read_s = std::chrono::duration<double>(read_end - read_start).count();
            const double convert_s = std::chrono::duration<double>(convert_end - convert_start).count();
            const double solve_s = std::chrono::duration<double>(solve_end - solve_start).count();
            std::cout << "matrix=" << args.matrix << '\n'
                      << "rows=" << n << '\n'
                      << "nnz=" << sparse.entries.size() << '\n'
                      << "block_size=" << args.block_size << '\n'
                      << "mpi_processes=" << processes << '\n'
                      << "omp_threads=" << args.threads << '\n'
                      << "read_time_s=" << read_s << '\n'
                      << "conversion_time_s=" << convert_s << '\n'
                      << "solve_time_s=" << solve_s << '\n'
                      << "iterations=" << iterations << '\n'
                      << "relative_residual=" << std::sqrt(residual_error) / norm_b << '\n'
                      << "solution_error=" << std::sqrt(solution_error / static_cast<double>(n)) << '\n'
                      << "padding_overhead=" << matrix.padding_ratio() << '\n';
        }
    } catch (const std::exception &error) {
        if (rank == 0) std::cerr << error.what() << '\n';
        MPI_Abort(MPI_COMM_WORLD, 2);
    }
    MPI_Finalize();
    return 0;
}
