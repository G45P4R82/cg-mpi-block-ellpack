#include "matrix_market.hpp"

#include <fstream>
#include <sstream>
#include <stdexcept>

namespace {

struct MMHeader {
    int rows = 0;
    int cols = 0;
    int entries = 0;
    bool symmetric = false;
};

MMHeader parse_header(std::istream &input, const std::string &path) {
    std::string line;
    if (!std::getline(input, line) || line.rfind("%%MatrixMarket", 0) != 0)
        throw std::runtime_error("cabecalho Matrix Market invalido: " + path);
    std::istringstream header(line);
    std::string banner, object, format, field, symmetry;
    header >> banner >> object >> format >> field >> symmetry;
    if (object != "matrix" || format != "coordinate" || field != "real")
        throw std::runtime_error("esperado Matrix Market coordinate real: " + path);
    MMHeader info;
    info.symmetric = (symmetry == "symmetric");

    do {
        if (!std::getline(input, line)) throw std::runtime_error("dimensoes ausentes: " + path);
    } while (line.empty() || line[0] == '%');
    std::istringstream dimensions(line);
    dimensions >> info.rows >> info.cols >> info.entries;
    if (info.rows != info.cols) throw std::runtime_error("CG exige matriz quadrada: " + path);
    return info;
}

}  // namespace

SparseMatrix read_matrix_market(const std::string &path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("nao foi possivel abrir: " + path);

    const MMHeader info = parse_header(input, path);
    SparseMatrix matrix{info.rows, info.cols, {}};
    matrix.entries.reserve(info.symmetric ? static_cast<std::size_t>(info.entries) * 2 : info.entries);
    for (int k = 0; k < info.entries; ++k) {
        int row = 0, col = 0;
        double value = 0.0;
        input >> row >> col >> value;
        --row;
        --col;
        matrix.entries.push_back({row, col, value});
        if (info.symmetric && row != col) matrix.entries.push_back({col, row, value});
    }
    return matrix;
}

SparseMatrix read_matrix_market_local(const std::string &path,
                                      int first_row,
                                      int row_count) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("nao foi possivel abrir: " + path);

    const MMHeader info = parse_header(input, path);
    SparseMatrix matrix{info.rows, info.cols, {}};
    // reserva estimada: fracao proporcional ao intervalo local
    const double fraction = info.rows > 0 ?
        static_cast<double>(row_count) / static_cast<double>(info.rows) : 0.0;
    const std::size_t estimate = static_cast<std::size_t>(
        (info.symmetric ? 2.0 : 1.0) * fraction * info.entries);
    matrix.entries.reserve(estimate + 16);

    const int last_row = first_row + row_count;
    for (int k = 0; k < info.entries; ++k) {
        int row = 0, col = 0;
        double value = 0.0;
        input >> row >> col >> value;
        --row;
        --col;
        if (row >= first_row && row < last_row) {
            matrix.entries.push_back({row, col, value});
        }
        if (info.symmetric && row != col && col >= first_row && col < last_row) {
            matrix.entries.push_back({col, row, value});
        }
    }
    return matrix;
}
