CXX ?= mpicxx
CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra -Wpedantic
OMPFLAGS ?= -fopenmp
BLAS_LIBS ?= -lblas
BIN_DIR ?= bin

.PHONY: all clean cg

all: cg

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

cg: $(BIN_DIR)
	$(CXX) $(CXXFLAGS) $(OMPFLAGS) src/matrix_market.cpp src/block_ellpack.cpp src/cg_mpi.cpp -Iinclude $(BLAS_LIBS) -o $(BIN_DIR)/cg_mpi

clean:
	rm -rf $(BIN_DIR)
