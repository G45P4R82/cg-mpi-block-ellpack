#include "matrix_market.hpp"

#include <fstream>
#include <sstream>
#include <stdexcept>

SparseMatrix read_matrix_market(const std::string &path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("nao foi possivel abrir: " + path);

    std::string line;
    if (!std::getline(input, line) || line.rfind("%%MatrixMarket", 0) != 0)
        throw std::runtime_error("cabecalho Matrix Market invalido");
    std::istringstream header(line);
    std::string banner, object, format, field, symmetry;
    header >> banner >> object >> format >> field >> symmetry;
    if (object != "matrix" || format != "coordinate" || field != "real")
        throw std::runtime_error("esperado Matrix Market coordinate real");
    const bool symmetric = symmetry == "symmetric";

    do {
        if (!std::getline(input, line)) throw std::runtime_error("dimensoes ausentes");
    } while (line.empty() || line[0] == '%');

    std::istringstream dimensions(line);
    int rows = 0, cols = 0, entries = 0;
    dimensions >> rows >> cols >> entries;
    if (rows != cols) throw std::runtime_error("CG exige matriz quadrada");

    SparseMatrix matrix{rows, cols, {}};
    matrix.entries.reserve(symmetric ? static_cast<std::size_t>(entries) * 2 : entries);
    for (int k = 0; k < entries; ++k) {
        int row = 0, col = 0;
        double value = 0.0;
        input >> row >> col >> value;
        --row;
        --col;
        matrix.entries.push_back({row, col, value});
        if (symmetric && row != col) matrix.entries.push_back({col, row, value});
    }
    return matrix;
}
