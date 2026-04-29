#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-train}"
if [[ $# -gt 0 ]]; then
  shift
fi

case "$ACTION" in
  train)
    python src/train.py \
      --run-name train_reference \
      --epochs 10 \
      --batch-size 4 \
      "$@"
    ;;
  validate)
    python src/validate.py \
      --checkpoint results/train_reference/checkpoints/best.pt \
      --split val \
      --run-name val_reference \
      "$@"
    ;;
  test)
    python src/test.py \
      --checkpoint results/train_reference/checkpoints/best.pt \
      --run-name test_reference \
      --save-max-preds 20 \
      "$@"
    ;;
  *)
    echo "Usage: bash 02-run_ml_pipeline.sh [train|validate|test] [extra args]"
    exit 1
    ;;
esac
