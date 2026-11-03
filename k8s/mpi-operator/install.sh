#!/usr/bin/env bash
set -euo pipefail

OPERATOR_VERSION="${OPERATOR_VERSION:-v0.8.2}"
OPERATOR_MANIFEST="https://raw.githubusercontent.com/kubeflow/mpi-operator/${OPERATOR_VERSION}/deploy/v2beta1/mpi-operator.yaml"
ARM64_DIGEST="sha256:da2b6c21471326dbccacb22cdf2ac4e417fc12581057101382276e99396480fb"

kubectl apply --server-side -f "$OPERATOR_MANIFEST"
kubectl patch deployment mpi-operator -n mpi-operator --type=merge -p \
  "{\"spec\":{\"template\":{\"spec\":{\"nodeSelector\":{\"kubernetes.io/arch\":\"arm64\"},\"containers\":[{\"name\":\"mpi-operator\",\"image\":\"mpioperator/mpi-operator@${ARM64_DIGEST}\"}]}}}}"
kubectl rollout status -n mpi-operator deployment/mpi-operator --timeout=300s
kubectl get crd mpijobs.kubeflow.org
