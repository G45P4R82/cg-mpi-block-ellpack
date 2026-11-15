#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="${K8S_NAMESPACE:-hpc-cg}"
RUN_DIR="${RUN_DIR:-${ROOT_DIR}/results/raw/cg-rerun-aks-$(date -u +%Y%m%dT%H%M%SZ)}"
KUBECTL=(kubectl)
if [[ -n "${KUBE_CONTEXT:-}" ]]; then
    KUBECTL+=(--context "$KUBE_CONTEXT")
fi
mkdir -p "$RUN_DIR"

cases=(
    "2 2 2"
    "2 2 1"
    "2 2 3"
    "2 4 1"
    "2 4 2"
    "2 4 3"
)

for case in "${cases[@]}"; do
    read -r mpi threads rep <<< "$case"
    job="cg-bcsstk16-b8-p${mpi}-t${threads}-r${rep}-hybrid-rerun"
    manifest="$RUN_DIR/${job}.yaml"
    log="$RUN_DIR/${job}.log"
    export JOB_NAME="$job" MATRIX=bcsstk16 BLOCK_SIZE=8 MPI_PROCS="$mpi"
    export OMP_THREADS="$threads" WORKER_CPU=2

    envsubst < "$ROOT_DIR/k8s/mpi-operator/cg-campaign.yaml.in" > "$manifest"
    "${KUBECTL[@]}" delete -n "$NAMESPACE" "mpijob/$job" --ignore-not-found >/dev/null
    "${KUBECTL[@]}" apply -n "$NAMESPACE" -f "$manifest" >/dev/null

    if "${KUBECTL[@]}" wait -n "$NAMESPACE" --for=condition=Succeeded \
        --timeout="${JOB_TIMEOUT:-3600}s" "mpijob/$job" >/dev/null; then
        launcher_pod=""
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
        printf 'FAILED %s\n' "$job" >&2
    fi
    "${KUBECTL[@]}" delete -n "$NAMESPACE" "mpijob/$job" --ignore-not-found >/dev/null || true
done

printf 'Rerun logs saved in %s\n' "$RUN_DIR"
