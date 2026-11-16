// Variante distribuida do Gradiente Conjugado.
// Cada rank armazena apenas as linhas locais do Block ELLPACK e usa
// comunicacao seletiva (MPI_Alltoallv) para popular as colunas remotas de p.
#include "block_ellpack_local.hpp"
#include "matrix_market.hpp"

#include <mpi.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <omp.h>
#include <stdexcept>
#include <string>
#include <vector>

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
    if (args.block_size < 1) throw std::runtime_error("--block-size deve ser positivo");
    if (args.threads < 1) throw std::runtime_error("--threads deve ser positivo");
    if (args.max_iterations < 1) throw std::runtime_error("--max-iters deve ser positivo");
    if (args.tolerance <= 0.0) throw std::runtime_error("--tol deve ser positivo");
    return args;
}

static double dot_local(const std::vector<double> &a,
                        const std::vector<double> &b,
                        int threads) {
    double result = 0.0;
    #pragma omp parallel for schedule(static) num_threads(threads) reduction(+:result)
    for (std::size_t i = 0; i < a.size(); ++i) result += a[i] * b[i];
    return result;
}

static int owner_of(int global_col, const std::vector<int> &displacements, int processes) {
    // Busca binaria pelo rank dono do indice global_col.
    int lo = 0, hi = processes - 1, result = processes - 1;
    while (lo <= hi) {
        const int mid = (lo + hi) / 2;
        if (displacements[mid] <= global_col) {
            result = mid;
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }
    return result;
}

static int read_global_rows(const std::string &path) {
    // Leitura minima do header para descobrir o numero de linhas globais.
    // Cada rank executa, aproveitando o cache de pagina do SO.
    SparseMatrix header_only = read_matrix_market_local(path, 0, 0);
    return header_only.rows;
}

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
    int rank = 0, processes = 1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &processes);
    try {
        const Args args = parse_args(argc, argv);

        const auto read_start = std::chrono::steady_clock::now();
        const int n = read_global_rows(args.matrix);
        std::vector<int> counts(processes), displacements(processes);
        for (int p = 0; p < processes; ++p) {
            counts[p] = (n * (p + 1)) / processes - (n * p) / processes;
            displacements[p] = (n * p) / processes;
        }
        const int first = displacements[rank];
        const int local_rows = counts[rank];

        SparseMatrix local_sparse = read_matrix_market_local(args.matrix, first, local_rows);
        const auto read_end = std::chrono::steady_clock::now();

        const std::size_t local_original_nnz = local_sparse.entries.size();

        const auto convert_start = std::chrono::steady_clock::now();
        BlockELLLocal matrix(local_sparse, args.block_size, first, local_rows);
        local_sparse.entries.clear();
        local_sparse.entries.shrink_to_fit();
        const auto convert_end = std::chrono::steady_clock::now();

        // Monta a lista de colunas remotas que preciso receber por rank
        // dono. Para cada coluna referenciada fora do meu intervalo local,
        // registramos o dono e armazenamos a posicao global.
        const auto &referenced = matrix.referenced_columns();
        std::vector<std::vector<int>> recv_requests_by_src(processes);
        for (int col : referenced) {
            if (col < 0 || col >= n) continue;
            if (col >= first && col < first + local_rows) continue;
            const int src = owner_of(col, displacements, processes);
            recv_requests_by_src[src].push_back(col);
        }
        // Compila recv_indices em um unico vetor + offsets por src.
        std::vector<int> recv_counts(processes, 0), recv_displs(processes, 0);
        std::vector<int> recv_global_indices;
        for (int src = 0; src < processes; ++src) {
            recv_displs[src] = static_cast<int>(recv_global_indices.size());
            recv_counts[src] = static_cast<int>(recv_requests_by_src[src].size());
            recv_global_indices.insert(recv_global_indices.end(),
                                       recv_requests_by_src[src].begin(),
                                       recv_requests_by_src[src].end());
        }

        // Troca os pedidos: cada rank conta quantos indices preciso de
        // cada dest e envia os indices globais. O outro lado recebe e
        // cria o plano de envio.
        std::vector<int> send_counts(processes, 0);
        MPI_Alltoall(recv_counts.data(), 1, MPI_INT,
                     send_counts.data(), 1, MPI_INT, MPI_COMM_WORLD);
        std::vector<int> send_displs(processes, 0);
        int total_send = 0;
        for (int p = 0; p < processes; ++p) {
            send_displs[p] = total_send;
            total_send += send_counts[p];
        }
        std::vector<int> send_global_indices(total_send);
        MPI_Alltoallv(recv_global_indices.data(), recv_counts.data(), recv_displs.data(), MPI_INT,
                      send_global_indices.data(), send_counts.data(), send_displs.data(), MPI_INT,
                      MPI_COMM_WORLD);
        // Converte indices globais em locais para o nosso vetor p_local.
        std::vector<int> send_local_indices(total_send);
        for (int i = 0; i < total_send; ++i) {
            send_local_indices[i] = send_global_indices[i] - first;
        }

        // Buffer global de p: inicializado com zeros em todas as colunas
        // que estao fora do intervalo local ou nao sao referenciadas.
        // Usamos tamanho N para manter compatibilidade com o SpMV baseado em
        // indices globais; as posicoes nao necessarias ficam intactas em zero.
        std::vector<double> p_global(n, 0.0);
        std::vector<double> p_local(local_rows, 0.0);
        std::vector<double> r_local(local_rows, 0.0);
        std::vector<double> b_local;
        std::vector<double> q_local;
        std::vector<double> x_local(local_rows, 0.0);

        // b = A * x_true, onde x_true = vetor de 1s.
        std::vector<double> x_true_global(n, 1.0);
        matrix.spmv(x_true_global, b_local, args.threads);
        x_true_global.clear();
        x_true_global.shrink_to_fit();

        r_local = b_local;
        p_local = r_local;
        double local_rho = dot_local(r_local, r_local, args.threads), rho = 0.0;
        MPI_Allreduce(&local_rho, &rho, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
        const double norm_b = std::sqrt(rho);

        // Buffers de troca para o halo exchange seletivo.
        std::vector<double> send_buffer(total_send);
        std::vector<double> recv_buffer(recv_global_indices.size());

        const auto solve_start = std::chrono::steady_clock::now();
        int iterations = 0;
        double relative_residual = 1.0;
        std::size_t allgather_bytes = 0;
        for (; iterations < args.max_iterations && norm_b > 0.0; ++iterations) {
            // Escreve meu p_local em p_global para que o SpMV veja minhas
            // colunas locais sem troca adicional.
            for (int i = 0; i < local_rows; ++i) {
                p_global[first + i] = p_local[i];
            }
            // Empacota os valores pedidos pelos outros ranks.
            for (int i = 0; i < total_send; ++i) {
                send_buffer[i] = p_local[send_local_indices[i]];
            }
            MPI_Alltoallv(send_buffer.data(), send_counts.data(), send_displs.data(), MPI_DOUBLE,
                          recv_buffer.data(), recv_counts.data(), recv_displs.data(), MPI_DOUBLE,
                          MPI_COMM_WORLD);
            allgather_bytes += (total_send + recv_buffer.size()) * sizeof(double);
            // Distribui os valores recebidos no p_global.
            for (std::size_t i = 0; i < recv_global_indices.size(); ++i) {
                p_global[recv_global_indices[i]] = recv_buffer[i];
            }

            matrix.spmv(p_global, q_local, args.threads);
            const double local_pq = dot_local(p_local, q_local, args.threads);
            double pq = 0.0;
            MPI_Allreduce(&local_pq, &pq, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
            if (!(pq > 0.0)) throw std::runtime_error("p^T A p nao positivo; matriz pode nao ser SPD");
            const double alpha = rho / pq;
            #pragma omp parallel for schedule(static) num_threads(args.threads)
            for (int i = 0; i < local_rows; ++i) {
                x_local[i] += alpha * p_local[i];
                r_local[i] -= alpha * q_local[i];
            }
            const double local_new_rho = dot_local(r_local, r_local, args.threads);
            double new_rho = 0.0;
            MPI_Allreduce(&local_new_rho, &new_rho, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
            relative_residual = std::sqrt(new_rho) / norm_b;
            if (relative_residual <= args.tolerance) { ++iterations; break; }
            const double beta = new_rho / rho;
            #pragma omp parallel for schedule(static) num_threads(args.threads)
            for (int i = 0; i < local_rows; ++i) p_local[i] = r_local[i] + beta * p_local[i];
            rho = new_rho;
        }
        const auto solve_end = std::chrono::steady_clock::now();

        // Validacao: calcula ||b - A*x_computed|| atraves de SpMV local.
        // Reutiliza o mesmo mecanismo de halo exchange sobre x_local.
        for (int i = 0; i < local_rows; ++i) {
            p_global[first + i] = x_local[i];
        }
        for (int i = 0; i < total_send; ++i) {
            send_buffer[i] = x_local[send_local_indices[i]];
        }
        MPI_Alltoallv(send_buffer.data(), send_counts.data(), send_displs.data(), MPI_DOUBLE,
                      recv_buffer.data(), recv_counts.data(), recv_displs.data(), MPI_DOUBLE,
                      MPI_COMM_WORLD);
        for (std::size_t i = 0; i < recv_global_indices.size(); ++i) {
            p_global[recv_global_indices[i]] = recv_buffer[i];
        }
        std::vector<double> ax_local;
        matrix.spmv(p_global, ax_local, args.threads);
        double local_residual_error = 0.0, local_solution_error = 0.0;
        #pragma omp parallel for schedule(static) num_threads(args.threads) reduction(+:local_residual_error,local_solution_error)
        for (int i = 0; i < local_rows; ++i) {
            const double residual = ax_local[i] - b_local[i];
            local_residual_error += residual * residual;
            const double solution_error = x_local[i] - 1.0;
            local_solution_error += solution_error * solution_error;
        }
        double residual_error = 0.0, solution_error = 0.0;
        MPI_Allreduce(&local_residual_error, &residual_error, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
        MPI_Allreduce(&local_solution_error, &solution_error, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);

        // Metricas agregadas de memoria.
        const double local_memory_mb = matrix.memory_bytes() / (1024.0 * 1024.0);
        double total_memory_mb = 0.0;
        double max_memory_mb = 0.0;
        MPI_Allreduce(&local_memory_mb, &total_memory_mb, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
        MPI_Allreduce(&local_memory_mb, &max_memory_mb, 1, MPI_DOUBLE, MPI_MAX, MPI_COMM_WORLD);
        unsigned long long local_nnz_ull = static_cast<unsigned long long>(local_original_nnz);
        unsigned long long total_nnz_ull = 0ULL;
        MPI_Allreduce(&local_nnz_ull, &total_nnz_ull, 1, MPI_UNSIGNED_LONG_LONG, MPI_SUM, MPI_COMM_WORLD);
        double local_padding = matrix.padding_ratio();
        double avg_padding = 0.0;
        double max_padding = 0.0;
        MPI_Allreduce(&local_padding, &avg_padding, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
        MPI_Allreduce(&local_padding, &max_padding, 1, MPI_DOUBLE, MPI_MAX, MPI_COMM_WORLD);
        avg_padding /= processes;
        unsigned long long send_bytes_ull = static_cast<unsigned long long>(allgather_bytes);
        unsigned long long total_comm_bytes = 0ULL;
        MPI_Allreduce(&send_bytes_ull, &total_comm_bytes, 1, MPI_UNSIGNED_LONG_LONG, MPI_SUM, MPI_COMM_WORLD);

        if (rank == 0) {
            const double read_s = std::chrono::duration<double>(read_end - read_start).count();
            const double convert_s = std::chrono::duration<double>(convert_end - convert_start).count();
            const double solve_s = std::chrono::duration<double>(solve_end - solve_start).count();
            std::cout << "variant=distributed\n"
                      << "matrix=" << args.matrix << '\n'
                      << "rows=" << n << '\n'
                      << "nnz=" << total_nnz_ull << '\n'
                      << "block_size=" << args.block_size << '\n'
                      << "mpi_processes=" << processes << '\n'
                      << "omp_threads=" << args.threads << '\n'
                      << "read_time_s=" << read_s << '\n'
                      << "conversion_time_s=" << convert_s << '\n'
                      << "solve_time_s=" << solve_s << '\n'
                      << "iterations=" << iterations << '\n'
                      << "relative_residual=" << std::sqrt(residual_error) / norm_b << '\n'
                      << "solution_error=" << std::sqrt(solution_error / static_cast<double>(n)) << '\n'
                      << "padding_overhead=" << avg_padding << '\n'
                      << "padding_overhead_max=" << max_padding << '\n'
                      << "memory_total_mb=" << total_memory_mb << '\n'
                      << "memory_max_mb=" << max_memory_mb << '\n'
                      << "memory_avg_mb=" << total_memory_mb / processes << '\n'
                      << "comm_bytes=" << total_comm_bytes << '\n';
        }
    } catch (const std::exception &error) {
        if (rank == 0) std::cerr << error.what() << '\n';
        MPI_Abort(MPI_COMM_WORLD, 2);
    }
    MPI_Finalize();
    return 0;
}
