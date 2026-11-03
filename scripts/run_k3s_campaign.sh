#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="${K8S_NAMESPACE:-default}"
REPETITIONS="${REPETITIONS:-3}"
RUN_DIR="${RUN_DIR:-${ROOT_DIR}/results/raw/cg-campaign-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$RUN_DIR"

command -v kubectl >/dev/null 2>&1 || { echo 'kubectl nao encontrado' >&2; exit 1; }
command -v envsubst >/dev/null 2>&1 || { echo 'envsubst nao encontrado' >&2; exit 1; }

run_case() {
    local matrix="$1" block="$2" mpi="$3" threads="$4" rep="$5"
    local job="cg-${matrix}-b${block}-p${mpi}-t${threads}-r${rep}"
    local manifest="${RUN_DIR}/${job}.yaml"
    local log="${RUN_DIR}/${job}.log"
    export JOB_NAME="$job" MATRIX="$matrix" BLOCK_SIZE="$block"
    export MPI_PROCS="$mpi" OMP_THREADS="$threads"

    envsubst < "$ROOT_DIR/k8s/mpi-operator/cg-campaign.yaml.in" > "$manifest"
    kubectl delete -n "$NAMESPACE" "mpijob/$job" --ignore-not-found >/dev/null
    kubectl apply -n "$NAMESPACE" -f "$manifest" >/dev/null
    if kubectl wait -n "$NAMESPACE" --for=condition=Succeeded \
        --timeout="${JOB_TIMEOUT:-3600}s" "mpijob/$job" >/dev/null; then
        kubectl logs -n "$NAMESPACE" -l "training.kubeflow.org/job-name=$job" \
            -c cg-launcher > "$log" 2>&1 || true
        printf 'SUCCESS %s\n' "$job"
    else
        kubectl get -n "$NAMESPACE" mpijob "$job" -o json > "${log%.log}.status.json" || true
        kubectl logs -n "$NAMESPACE" -l "training.kubeflow.org/job-name=$job" \
            -c cg-launcher > "$log" 2>&1 || true
        printf 'FAILED %s\n' "$job" >&2
    fi
    kubectl delete -n "$NAMESPACE" "mpijob/$job" --ignore-not-found >/dev/null || true
}

# Block-size study on all matrices, using two MPI ranks and one thread/rank.
for matrix in bcsstk34 bcsstk14 bcsstk16; do
    for block in 4 8 16 32; do
        for rep in $(seq 1 "$REPETITIONS"); do
            run_case "$matrix" "$block" 2 1 "$rep"
        done
    done
done

# Strong scaling on the largest matrix.
for mpi in 1 2 4; do
    for rep in $(seq 1 "$REPETITIONS"); do
        run_case bcsstk16 8 "$mpi" 1 "$rep"
    done
done

# Hybrid MPI/OpenMP scaling.
for threads in 1 2 4; do
    for rep in $(seq 1 "$REPETITIONS"); do
        run_case bcsstk16 8 2 "$threads" "$rep"
    done
done

printf 'Campaign logs saved in %s\n' "$RUN_DIR"
