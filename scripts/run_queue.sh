#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QUEUE_FILE="${QUEUE_FILE:-$ROOT_DIR/experiments/queue.tsv}"
RUN_DIR="${RUN_DIR:-$ROOT_DIR/results/queue-$(date -u +%Y%m%dT%H%M%SZ)}"
STATUS_FILE="${STATUS_FILE:-$RUN_DIR/queue-status.tsv}"
NAMESPACE="${K8S_NAMESPACE:-default}"
KUBECTL=(kubectl)
if [[ -n "${KUBE_CONTEXT:-}" ]]; then
    KUBECTL+=(--context "$KUBE_CONTEXT")
fi

mkdir -p "$RUN_DIR"
command -v "${KUBECTL[0]}" >/dev/null 2>&1 || { printf 'kubectl nao encontrado\n' >&2; exit 1; }
command -v envsubst >/dev/null 2>&1 || { printf 'envsubst nao encontrado\n' >&2; exit 1; }
command -v flock >/dev/null 2>&1 || { printf 'flock nao encontrado\n' >&2; exit 1; }

exec 9>"$STATUS_FILE.lock"
flock -n 9 || { printf 'outra fila ja esta rodando\n' >&2; exit 1; }

if [[ ! -f "$STATUS_FILE" ]]; then
    printf 'id\tstatus\tjob\tupdated\n' > "$STATUS_FILE"
fi

record_status() {
    printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$STATUS_FILE"
}

latest_status() {
    awk -F '\t' -v id="$1" '$1 == id { status=$2 } END { print status }' "$STATUS_FILE"
}

wait_for_success() {
    local job="$1" deadline=$((SECONDS + ${JOB_TIMEOUT:-3600})) conditions
    while (( SECONDS < deadline )); do
        conditions=$("${KUBECTL[@]}" get -n "$NAMESPACE" mpijob "$job" \
            -o jsonpath='{range .status.conditions[*]}{.type}={.status}{"\n"}{end}' \
            2>/dev/null || true)
        [[ "$conditions" == *"Succeeded=True"* ]] && return 0
        [[ "$conditions" == *"Failed=True"* ]] && return 1
        sleep 5
    done
    return 1
}

launcher_pod() {
    local job="$1" pod
    while IFS= read -r pod; do
        if [[ "$pod" == *-launcher-* ]]; then
            printf '%s\n' "$pod"
            return 0
        fi
    done < <("${KUBECTL[@]}" get pods -n "$NAMESPACE" \
        -l "training.kubeflow.org/job-name=$job" \
        -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')
    return 1
}

tail -n +2 "$QUEUE_FILE" | while IFS=$'\t' read -r id matrix block mpi threads repetition label; do
    [[ -z "$id" ]] && continue
    [[ "$(latest_status "$id")" == "SUCCESS" ]] && continue

    job="cg-${matrix}-b${block}-p${mpi}-t${threads}-r${repetition}-${label}-${id}"
    item_dir="$RUN_DIR/$id"
    manifest="$item_dir/manifest.yaml"
    log="$item_dir/launcher.log"
    mkdir -p "$item_dir"
    export JOB_NAME="$job" MATRIX="$matrix" BLOCK_SIZE="$block"
    export MPI_PROCS="$mpi" OMP_THREADS="$threads" WORKER_CPU="${WORKER_CPU_OVERRIDE:-$threads}"

    envsubst < "$ROOT_DIR/k8s/mpi-operator/cg-campaign.yaml.in" > "$manifest"
    record_status "$id" RUNNING "$job"
    "${KUBECTL[@]}" delete -n "$NAMESPACE" "mpijob/$job" --ignore-not-found >/dev/null
    "${KUBECTL[@]}" apply -n "$NAMESPACE" -f "$manifest" >/dev/null

    if wait_for_success "$job"; then
        pod="$(launcher_pod "$job" || true)"
        [[ -n "$pod" ]] && "${KUBECTL[@]}" logs -n "$NAMESPACE" "$pod" -c cg-launcher > "$log" 2>&1 || true
        if [[ -s "$log" ]] && grep -q '^solve_time_s=' "$log"; then
            record_status "$id" SUCCESS "$job"
            printf 'SUCCESS %s\n' "$id"
        else
            "${KUBECTL[@]}" get -n "$NAMESPACE" mpijob "$job" -o json > "$item_dir/status.json" || true
            record_status "$id" FAILED "$job"
            printf 'FAILED %s\n' "$id" >&2
        fi
    else
        "${KUBECTL[@]}" get -n "$NAMESPACE" mpijob "$job" -o json > "$item_dir/status.json" || true
        "${KUBECTL[@]}" logs -n "$NAMESPACE" -l "training.kubeflow.org/job-name=$job" -c cg-launcher > "$log" 2>&1 || true
        record_status "$id" FAILED "$job"
        printf 'FAILED %s\n' "$id" >&2
    fi
    "${KUBECTL[@]}" delete -n "$NAMESPACE" "mpijob/$job" --ignore-not-found >/dev/null || true
done

printf 'queue finished: %s\n' "$RUN_DIR"
