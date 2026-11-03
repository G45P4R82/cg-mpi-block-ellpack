FROM --platform=$TARGETPLATFORM mpioperator/mpi-pi:mpich

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ libmpich-dev mpich libopenblas-dev openssh-server \
    && rm -rf /var/lib/apt/lists/*

COPY include /tmp/cg/include
COPY src /tmp/cg/src
COPY matrices /opt/cg/matrices

RUN mkdir -p /opt/cg/bin \
    && mpicxx -O3 -std=c++17 -fopenmp \
       /tmp/cg/src/matrix_market.cpp \
       /tmp/cg/src/block_ellpack.cpp \
       /tmp/cg/src/cg_mpi.cpp \
       -I/tmp/cg/include -lopenblas -o /opt/cg/bin/cg_mpi \
    && rm -rf /tmp/cg \
    && chown -R mpiuser:mpiuser /opt/cg

USER mpiuser
