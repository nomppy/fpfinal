# Foreign Policy Discourse Pipeline (Chinese compute)

This repository implements a reproducible, modular pipeline for measuring outward-engagement discourse adjustment in Chinese-language foreign policy texts since 2012. The pipeline is designed to run on a laptop, with deterministic sampling options and on-disk caches to make results reproducible.

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

## Pipeline stages

1) **Collect sources** (`01_collect.py`)
   - Downloads source documents and stores raw HTML in `data/raw/` and parsed JSON in `data/parsed/`.
   - Uses the date range in `config/analysis.yaml` unless overridden by `--analysis-start/--analysis-end`.
   - Uses `data/cache/` for HTTP response caching. Use `--force` to bypass cache.

2) **Segment documents** (`02_segment.py`)
   - Loads `data/parsed/docs.jsonl`, re-parses cached HTML, and writes segmented JSON to `data/segments/`.
   - Outputs `data/segments/segments.jsonl`.

3) **Embed segments** (`03_embed.py`)
   - Generates embeddings for non-heading segments using the model in `config/models.yaml`.
   - Writes `data/segments/segments_embedded.jsonl` and embedding cache files in `data/embeddings/`.
   - Use `--force` to regenerate embeddings.

4) **Score axes & outward filter** (`04_score_axes.py`)
   - Builds axis vectors from `config/axes.yaml` and scores each segment.
   - Applies outward-engagement thresholds from `config/analysis.yaml`.
   - Outputs `data/segments/segments_scored.jsonl`.

5) **Run analyses** (`05_run_tests.py`)
   - Writes tables to `outputs/tables/` and figures to `outputs/figures/`.
   - Includes trend, coupling, keyness, slogans, and elasticity outputs.

6) **Export excerpts** (`06_export_excerpt_bank.py`)
   - Generates `outputs/excerpts/excerpt_bank.jsonl` from scored segments.

## Configuration

- `config/sources.yaml`: source URLs, sampling caps, and scraping metadata.
- `config/analysis.yaml`: date ranges, thresholds, binning, keyness, and slogan settings.
- `config/models.yaml`: embedding model settings and cache mode.
- `config/axes.yaml`: axis seed sentences.
- `config/slogans_curated.txt`: curated slogans list (one per line).
- `config/stoplist_slogans.txt`: stoplist for slogan extraction.

## Reproducibility checklist

For reproducible runs, lock down both configuration and caches.

1) **Pin versions**
   - Use the `requirements.txt` exact versions with Python 3.11.

2) **Fix sampling** (press briefings)
   - Set `sample_years`, `sample_strategy`, and `sample_seed` in `config/sources.yaml` under `mfa_pressers`.
   - Alternatively, set `max_docs_per_year` and `sample_strategy: even` for deterministic even-spacing.

3) **Fix analysis date ranges**
   - Set `analysis_start`/`analysis_end` in `config/analysis.yaml` or pass `--analysis-start/--analysis-end` to `01_collect.py`.
   - For lightweight, deterministic runs, enable `sample_mode: true` and set `sample_year` in `config/analysis.yaml` to restrict analysis to a single year.

4) **Persist caches**
   - Keep `data/cache/` and `data/raw/` under versioned storage for source reproducibility.
   - Keep `data/embeddings/` if you want to reuse exact embeddings across runs.
   - Use `--force` only when you want to intentionally refresh cached content.

5) **Record model settings**
   - `config/models.yaml` controls the embedding model name, device, and cache mode (`embeddings` or `scores_only`).

## Data layout

```
config/                # Configuration files
scripts/               # Helper scripts
src/                   # Pipeline modules

data/cache/             # Cached HTML responses (per source URL)
data/raw/               # Raw HTML snapshots
data/parsed/            # Parsed JSON documents

# After segmentation/embedding/scoring

data/segments/          # Segment JSON files + jsonl aggregations

data/embeddings/        # Embedding caches (.npz per doc)

outputs/tables/         # CSV tables
outputs/figures/        # PNG figures
outputs/excerpts/       # excerpt_bank.jsonl
```

## Notes

- URLs and sampling behavior live entirely in `config/sources.yaml`; no URLs are hard-coded in the pipeline.
- `mfa_pressers` collection relies on live pages unless cached; store `data/cache/` and `data/raw/` for strict reproducibility.
- Set `cache_mode: scores_only` in `config/models.yaml` if disk space is limited (embedding caches won’t be written).
