#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "Installation complete."
python -c "import torch; print('torch', torch.__version__, 'cuda_available', torch.cuda.is_available())"
