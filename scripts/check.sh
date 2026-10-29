#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
python -m compileall -q learning_japanese tests
python -m unittest discover -s tests -v
