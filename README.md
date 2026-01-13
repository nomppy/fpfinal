# Foreign Policy Discourse Pipeline (Chinese compute)

This repository implements a reproducible, modular pipeline for measuring outward-engagement discourse adjustment since 2012. It is designed for laptop-friendly execution with caching and configuration-driven sources.

## Quickstart

1) **Setup**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) **Run the pipeline**

```bash
python 01_collect.py --config-dir config
python 02_segment.py --config-dir config
python 03_embed.py --config-dir config
python 04_score_axes.py --config-dir config
python 05_run_tests.py --config-dir config
python 06_export_excerpt_bank.py --config-dir config
```

3) **Outputs**

- Tables: `outputs/tables/`
- Figures: `outputs/figures/`
- Excerpts: `outputs/excerpts/excerpt_bank.jsonl`

4) **Edit axis seeds & curated slogans**

- Axis seed sentences: `config/axes.yaml`
- Curated slogans list: `config/slogans_curated.txt` (one slogan per line)

## Configuration

- `config/sources.yaml`: all URL policies and document lists.
- `config/analysis.yaml`: analysis range, thresholds, binning, and keyness settings.
- `config/models.yaml`: embedding model and caching mode.

## Notes

- All URLs are defined in YAML configuration files; code does not hardcode URLs.
- Cached HTML is stored under `data/cache/` and `data/raw/`.
- For tight disk constraints, set `cache_mode: scores_only` in `config/models.yaml`.
