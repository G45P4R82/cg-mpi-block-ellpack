# MPI Operator no k3s

O projeto usa o Kubeflow MPI Operator para criar um launcher e workers MPI no
Kubernetes. O Operator foi instalado no namespace de sistema `mpi-operator`.

## Estado instalado

- CRD: `mpijobs.kubeflow.org`;
- API: `kubeflow.org/v2beta1`;
- Operator: release `v0.8.2`;
- imagem do controller fixada no digest ARM64:

```text
mpioperator/mpi-operator@sha256:da2b6c21471326dbccacb22cdf2ac4e417fc12581057101382276e99396480fb
```

A tag `mpioperator/mpi-operator:0.8.2` inicialmente falhou porque o runtime
tentou resolver uma plataforma incompatível. O deployment foi fixado em
ARM64 (`kubernetes.io/arch=arm64`) e no digest correspondente.

## Verificacao

```bash
kubectl get crd mpijobs.kubeflow.org
kubectl get pods -n mpi-operator
```

Nao publique contexto, endpoint, nomes de nos ou credenciais.

## Aplicacao do MPIJob

O arquivo `cg-mpijob.yaml.example` e um template. Antes de aplicar, substitua
somente `CG_IMAGE` por uma imagem ARM64 que contenha MPICH, `sshd`, o executavel
CG e as matrizes, e `MATRIX_PATH` pelo caminho interno da imagem.

## Construir a imagem ARM64

Defina uma imagem em um registry acessivel pelos nos:

```bash
docker buildx build --platform linux/arm64 \
  -t REGISTRY/cg-mpi:arm64 \
  --push .
```

Nao coloque tokens do registry no Git. Se o registry for privado, crie um
`imagePullSecret` no namespace de execucao e adicione `imagePullSecrets` aos
pods do `MPIJob`.
