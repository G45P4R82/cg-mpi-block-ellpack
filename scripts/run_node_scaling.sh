#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QUEUE_FILE="${QUEUE_FILE:-$ROOT_DIR/experiments/node-scaling.tsv}"
RUN_DIR="${RUN_DIR:-$ROOT_DIR/results/node-scaling-$(date -u +%Y%m%dT%H%M%SZ)}"
STATUS_FILE="${STATUS_FILE:-$RUN_DIR/node-status.tsv}"
NAMESPACE="${K8S_NAMESPACE:-hpc-cg}"
NODE_POOL_RAW="${NODE_POOL:-tvbox02,tvbox03,cluster-tvbox-04,cluster-tvbox-05}"
LAUNCHER_POOL_RAW="${LAUNCHER_POOL:-tvbox02,tvbox03,cluster-tvbox-04,cluster-tvbox-05}"

KUBECTL=(kubectl)
if [[ -n "${KUBE_CONTEXT:-}" ]]; then
    KUBECTL+=(--context "$KUBE_CONTEXT")
fi

mkdir -p "$RUN_DIR"
command -v "${KUBECTL[0]}" >/dev/null 2>&1 || { printf 'kubectl nao encontrado\n' >&2; exit 1; }
command -v envsubst >/dev/null 2>&1 || { printf 'envsubst nao encontrado\n' >&2; exit 1; }

IFS=',' read -r -a NODE_POOL_ARR <<< "$NODE_POOL_RAW"
IFS=',' read -r -a LAUNCHER_POOL_ARR <<< "$LAUNCHER_POOL_RAW"
launcher_quoted=()
for n in "${LAUNCHER_POOL_ARR[@]}"; do
    launcher_quoted+=("\"$n\"")
done
launcher_pool_values_global=$(IFS=,; printf '%s' "${launcher_quoted[*]}")
unset IFS

build_pool() {
    local requested="$1"
    local selected=()
    for node in "${NODE_POOL_ARR[@]}"; do
        [[ ${#selected[@]} -ge "$requested" ]] && break
        selected+=("$node")
    done
    local quoted=()
    for n in "${selected[@]}"; do
        quoted+=("\"$n\"")
    done
    local joined
    joined=$(IFS=,; printf '%s' "${quoted[*]}")
    printf '%s' "$joined"
}

if [[ ! -f "$STATUS_FILE" ]]; then
    printf 'id\tstatus\tjob\tnodes\tpods\tupdated\n' > "$STATUS_FILE"
fi

record_status() {
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$5" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$STATUS_FILE"
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

collect_pod_placement() {
    local job="$1"
    "${KUBECTL[@]}" get pods -n "$NAMESPACE" \
        -l "training.kubeflow.org/job-name=$job" \
        -o jsonpath='{range .items[*]}{.metadata.name}={.spec.nodeName};{end}'
}

tail -n +2 "$QUEUE_FILE" | while IFS=$'\t' read -r id matrix block mpi threads repetition nodes label; do
    [[ -z "$id" ]] && continue
    [[ "$(latest_status "$id")" == "SUCCESS" ]] && continue

    job="cg-${matrix}-b${block}-p${mpi}-t${threads}-r${repetition}-${label}-${id}"
    item_dir="$RUN_DIR/$id"
    manifest="$item_dir/manifest.yaml"
    log="$item_dir/launcher.log"
    placement_file="$item_dir/pod-placement.txt"
    mkdir -p "$item_dir"
    node_pool_values="$(build_pool "$nodes")"

    # Aplica anti-affinity apenas quando queremos 1 worker por no (mpi == nodes).
    # Caso contrario (ex: 4 workers em 2 nos), permitimos co-location para
    # 2 workers por no.
    if [[ "$nodes" -gt 1 && "$mpi" -eq "$nodes" ]]; then
        anti_affinity='requiredDuringSchedulingIgnoredDuringExecution: [{labelSelector: {matchExpressions: [{key: training.kubeflow.org/job-name, operator: In, values: ['"$job"']}, {key: training.kubeflow.org/job-role, operator: In, values: [worker]}]}, topologyKey: kubernetes.io/hostname}]'
    else
        anti_affinity='{}'
    fi

    export JOB_NAME="$job" MATRIX="$matrix" BLOCK_SIZE="$block"
    export MPI_PROCS="$mpi" OMP_THREADS="$threads"
    export WORKER_CPU="${WORKER_CPU_OVERRIDE:-$threads}"
    export NODE_COUNT="$nodes"
    export NODE_POOL="$node_pool_values"
    export LAUNCHER_POOL="$launcher_pool_values_global"
    export WORKER_ANTI_AFFINITY="$anti_affinity"

    envsubst < "$ROOT_DIR/k8s/mpi-operator/cg-nodes.yaml.in" > "$manifest"
    record_status "$id" RUNNING "$job" "$nodes" ""
    "${KUBECTL[@]}" delete -n "$NAMESPACE" "mpijob/$job" --ignore-not-found --grace-period=0 --force >/dev/null 2>&1 || true
    sleep 3
    "${KUBECTL[@]}" apply -n "$NAMESPACE" -f "$manifest" >/dev/null

    # Coleta placement assim que os pods forem agendados, antes do wait
    placement_early=""
    for _ in $(seq 1 60); do
        placement_early="$(collect_pod_placement "$job" || true)"
        if [[ -n "$placement_early" && "$placement_early" == *"="*";"* ]]; then
            printf '%s\n' "$placement_early" > "$placement_file"
            break
        fi
        sleep 2
    done

    if wait_for_success "$job"; then
        pod="$(launcher_pod "$job" || true)"
        placement="$(collect_pod_placement "$job" || true)"
        if [[ -n "$placement" && "$placement" == *"="*";"* ]]; then
            printf '%s\n' "$placement" > "$placement_file"
        else
            placement="$placement_early"
        fi
        [[ -n "$pod" ]] && "${KUBECTL[@]}" logs -n "$NAMESPACE" "$pod" -c cg-launcher > "$log" 2>&1 || true
        if [[ -s "$log" ]] && grep -q '^solve_time_s=' "$log"; then
            record_status "$id" SUCCESS "$job" "$nodes" "$placement"
            printf 'SUCCESS %s (%s nos)\n' "$id" "$nodes"
        else
            "${KUBECTL[@]}" get -n "$NAMESPACE" mpijob "$job" -o json > "$item_dir/status.json" || true
            record_status "$id" FAILED "$job" "$nodes" "$placement"
            printf 'FAILED %s\n' "$id" >&2
        fi
    else
        placement="$(collect_pod_placement "$job" || true)"
        printf '%s\n' "$placement" > "$placement_file"
        "${KUBECTL[@]}" get -n "$NAMESPACE" mpijob "$job" -o json > "$item_dir/status.json" || true
        "${KUBECTL[@]}" logs -n "$NAMESPACE" -l "training.kubeflow.org/job-name=$job" -c cg-launcher > "$log" 2>&1 || true
        record_status "$id" FAILED "$job" "$nodes" "$placement"
        printf 'FAILED %s\n' "$id" >&2
    fi
    "${KUBECTL[@]}" delete -n "$NAMESPACE" "mpijob/$job" --ignore-not-found >/dev/null || true
done

printf 'node scaling finished: %s\n' "$RUN_DIR"
