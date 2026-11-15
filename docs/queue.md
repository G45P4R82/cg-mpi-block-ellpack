# Fila Reprodutivel de Experimentos

A fila estatica esta em `experiments/queue.tsv` e possui 54 configuracoes.
Cada linha recebe um ID unico (`q001` a `q054`). O runner executa uma linha por
vez e salva cada item em uma pasta separada:

```text
results/queue-<timestamp>/q001/
  manifest.yaml
  launcher.log
  status.json       # somente em falhas
```

O status geral fica em `queue-status.tsv`. A fila pode ser retomada sem repetir
itens com `SUCCESS`:

```bash
KUBE_CONTEXT=tvbox-k3s K8S_NAMESPACE=hpc-cg \
  RUN_DIR=results/queue-tvbox \
  bash scripts/run_queue.sh
```

Um lock em `queue-status.tsv.lock` impede duas filas simultaneas para o mesmo
diretorio de resultados.
