#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BITS="${1:-both}"

if [[ "$BITS" != "8bit" && "$BITS" != "16bit" && "$BITS" != "both" ]]; then
  echo "Usage: bash 02-run_ml_pipeline.sh [8bit|16bit|both]"
  exit 1
fi

python src/run_ml_pipeline.py --bits "$BITS"
