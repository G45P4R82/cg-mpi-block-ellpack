# Execucao MPI no k3s

O MPI Operator oficial `v0.8.2` foi instalado no k3s. O CRD usado e
`mpijobs.kubeflow.org`, na API `kubeflow.org/v2beta1`. O controller foi fixado
em uma imagem ARM64 por digest.

## Imagem da aplicacao

Ainda e necessario construir uma imagem ARM64 contendo:

- MPICH e `mpirun`;
- OpenMP e BLAS;
- `sshd`;
- usuario `mpiuser` e chaves SSH;
- `cg_mpi`;
- as matrizes de `matrices/`.

A mesma imagem sera usada pelo launcher e pelos workers.

## Execucao

```bash
cp k8s/mpi-operator/cg-mpijob.yaml.example k8s/mpi-operator/cg-mpijob.yaml
```

Substitua `CG_IMAGE` e `MATRIX_PATH`, valide e aplique:

```bash
kubectl apply --dry-run=server -f k8s/mpi-operator/cg-mpijob.yaml
kubectl apply -f k8s/mpi-operator/cg-mpijob.yaml
```

O launcher executara `mpirun` e os workers executarao `sshd`. Os logs devem
registrar leitura, conversao, solver, iteracoes, residuo e Block ELLPACK.
