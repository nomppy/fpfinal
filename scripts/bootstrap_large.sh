#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/bootstrap.sh
#   ANALYSIS_START=2012-01-01 ANALYSIS_END=2025-12-31 bash scripts/bootstrap.sh
#
# Assumes the repo contains:
#   requirements.txt
#   01_collect.py ... 06_export_excerpt_bank.py
#   config/ (YAMLs)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ANALYSIS_START="${ANALYSIS_START:-}"
ANALYSIS_END="${ANALYSIS_END:-}"
CONFIG_DIR="${CONFIG_DIR:-config}"

export PYTHONUTF8=1
export TOKENIZERS_PARALLELISM=false
export HF_HOME="${HF_HOME:-$ROOT_DIR/.cache/huggingface}"

mkdir -p .cache logs data/raw data/parsed outputs/tables outputs/figures outputs/excerpts

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.11+ first."
  exit 1
fi

# Create venv if missing
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# Activate venv
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip wheel setuptools

if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
else
  echo "WARNING: requirements.txt not found. Installing a minimal set."
  pip install requests beautifulsoup4 lxml pyyaml pandas numpy scipy scikit-learn matplotlib tqdm regex trafilatura sentence-transformers pytest
fi

run_step () {
  local step="$1"
  shift
  echo
  echo "=== Running: $step ==="
  python "$step" \
    --config-dir "$CONFIG_DIR" \
    ${ANALYSIS_START:+--analysis-start "$ANALYSIS_START"} \
    ${ANALYSIS_END:+--analysis-end "$ANALYSIS_END"} \
    "$@" 2>&1 | tee "logs/${step%.py}.log"
}

run_step 01_collect.py
run_step 02_segment.py
run_step 03_embed.py
run_step 04_score_axes.py
run_step 05_run_tests.py
run_step 06_export_excerpt_bank.py

echo
echo "Done."
echo "Tables:  outputs/tables/"
echo "Figures: outputs/figures/"
echo "Excerpts: outputs/excerpts/excerpt_bank.jsonl"
