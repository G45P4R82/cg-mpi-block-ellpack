#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="${K8S_NAMESPACE:-default}"
REPETITIONS="${REPETITIONS:-3}"
RUN_DIR="${RUN_DIR:-${ROOT_DIR}/results/raw/cg-campaign-$(date -u +%Y%m%dT%H%M%SZ)}"
KUBECTL=(kubectl)
if [[ -n "${KUBE_CONTEXT:-}" ]]; then
    KUBECTL+=(--context "$KUBE_CONTEXT")
fi
mkdir -p "$RUN_DIR"

command -v "${KUBECTL[0]}" >/dev/null 2>&1 || { echo 'kubectl nao encontrado' >&2; exit 1; }
command -v envsubst >/dev/null 2>&1 || { echo 'envsubst nao encontrado' >&2; exit 1; }

wait_for_success() {
    local namespace="$1" job="$2" timeout_seconds="${JOB_TIMEOUT:-3600}"
    local deadline=$((SECONDS + timeout_seconds))
    local conditions
    while (( SECONDS < deadline )); do
        conditions=$("${KUBECTL[@]}" get -n "$namespace" mpijob "$job" \
            -o jsonpath='{range .status.conditions[*]}{.type}={.status}{"\n"}{end}' \
            2>/dev/null || true)
        if [[ "$conditions" == *"Succeeded=True"* ]]; then
            return 0
        fi
        if [[ "$conditions" == *"Failed=True"* ]]; then
            return 1
        fi
        sleep 5
    done
    return 1
}

run_case() {
    local matrix="$1" block="$2" mpi="$3" threads="$4" rep="$5" label="${6:-}"
    local suffix=""
    local launcher_pod=""
    local worker_cpu="${WORKER_CPU_OVERRIDE:-$threads}"
    if [[ -n "$label" ]]; then
        suffix="-${label}"
    fi
    local job="cg-${matrix}-b${block}-p${mpi}-t${threads}-r${rep}${suffix}"
    local manifest="${RUN_DIR}/${job}.yaml"
    local log="${RUN_DIR}/${job}.log"
    export JOB_NAME="$job" MATRIX="$matrix" BLOCK_SIZE="$block"
    export MPI_PROCS="$mpi" OMP_THREADS="$threads"
    export WORKER_CPU="$worker_cpu"

    envsubst < "$ROOT_DIR/k8s/mpi-operator/cg-campaign.yaml.in" > "$manifest"
    "${KUBECTL[@]}" delete -n "$NAMESPACE" "mpijob/$job" --ignore-not-found >/dev/null
    "${KUBECTL[@]}" apply -n "$NAMESPACE" -f "$manifest" >/dev/null
    if wait_for_success "$NAMESPACE" "$job"; then
        while IFS= read -r pod; do
            if [[ "$pod" == *-launcher-* ]]; then
                launcher_pod="$pod"
                break
            fi
        done < <("${KUBECTL[@]}" get pods -n "$NAMESPACE" \
            -l "training.kubeflow.org/job-name=$job" \
            -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')
        if [[ -n "$launcher_pod" ]]; then
            "${KUBECTL[@]}" logs -n "$NAMESPACE" "$launcher_pod" \
                -c cg-launcher > "$log" 2>&1 || true
        fi
        if [[ -s "$log" ]] && grep -q '^solve_time_s=' "$log"; then
            printf 'SUCCESS %s\n' "$job"
        else
            "${KUBECTL[@]}" get -n "$NAMESPACE" mpijob "$job" -o json > "${log%.log}.status.json" || true
            printf 'FAILED %s\n' "$job" >&2
        fi
    else
        "${KUBECTL[@]}" get -n "$NAMESPACE" mpijob "$job" -o json > "${log%.log}.status.json" || true
        "${KUBECTL[@]}" logs -n "$NAMESPACE" -l "training.kubeflow.org/job-name=$job" \
            -c cg-launcher > "$log" 2>&1 || true
        printf 'FAILED %s\n' "$job" >&2
    fi
    "${KUBECTL[@]}" delete -n "$NAMESPACE" "mpijob/$job" --ignore-not-found >/dev/null || true
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
        run_case bcsstk16 8 "$mpi" 1 "$rep" strong
    done
done

# Hybrid MPI/OpenMP scaling.
for threads in 1 2 4; do
    for rep in $(seq 1 "$REPETITIONS"); do
        run_case bcsstk16 8 2 "$threads" "$rep" hybrid
    done
done

printf 'Campaign logs saved in %s\n' "$RUN_DIR"
