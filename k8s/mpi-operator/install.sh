#!/usr/bin/env bash
set -euo pipefail

OPERATOR_VERSION="${OPERATOR_VERSION:-v0.8.2}"
OPERATOR_MANIFEST="https://raw.githubusercontent.com/kubeflow/mpi-operator/${OPERATOR_VERSION}/deploy/v2beta1/mpi-operator.yaml"
OPERATOR_IMAGE="${OPERATOR_IMAGE:-mpioperator/mpi-operator:0.8.2}"
KUBECTL=(kubectl)
if [[ -n "${KUBE_CONTEXT:-}" ]]; then
  KUBECTL+=(--context "$KUBE_CONTEXT")
fi

"${KUBECTL[@]}" apply --server-side -f "$OPERATOR_MANIFEST"
"${KUBECTL[@]}" patch deployment mpi-operator -n mpi-operator --type=merge -p \
  "{\"spec\":{\"template\":{\"spec\":{\"nodeSelector\":{\"kubernetes.io/arch\":\"arm64\"},\"containers\":[{\"name\":\"mpi-operator\",\"image\":\"${OPERATOR_IMAGE}\",\"imagePullPolicy\":\"IfNotPresent\",\"args\":[\"-alsologtostderr\",\"--lock-namespace=mpi-operator\"]}]}}}}"
"${KUBECTL[@]}" rollout status -n mpi-operator deployment/mpi-operator --timeout=300s
"${KUBECTL[@]}" get crd mpijobs.kubeflow.org
