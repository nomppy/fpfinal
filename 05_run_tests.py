#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.tests.coupling import run_coupling
from src.tests.elasticity import cluster_embeddings, slogan_entropy
from src.tests.keyness import compute_keyness
from src.tests.slogans import extract_candidates, slogan_metrics, slogan_presence
from src.tests.trend import run_trend
from src.utils import jsonl_read, load_config_bundle, load_curated, load_stoplist, save_json


def percentile_threshold(values: list[float], pct: float) -> float:
    return float(np.percentile(values, pct * 100)) if values else 0.0


def run_keyness(rows: list[dict], analysis_cfg: dict) -> None:
    output_dir = Path("outputs/tables")
    output_dir.mkdir(parents=True, exist_ok=True)
    method = analysis_cfg["keyness"]["method"]
    n_min = analysis_cfg["keyness"]["ngram_min"]
    n_max = analysis_cfg["keyness"]["ngram_max"]
    top_n = analysis_cfg["keyness"]["top_n"]
    alpha = analysis_cfg["keyness"]["alpha"]

    df = pd.DataFrame([r for r in rows if r["scores"].get("is_outward")])
    if df.empty:
        return
    for year, group in df.groupby(df["date"].str.slice(0, 4)):
        sec_vals = group["scores"].apply(lambda x: x["security_axis"]).tolist()
        growth_vals = group["scores"].apply(lambda x: x["growth_axis"]).tolist()
        sec_hi = percentile_threshold(sec_vals, analysis_cfg["security_top_decile"])
        sec_lo = percentile_threshold(sec_vals, analysis_cfg["security_bottom_decile"])
        grow_hi = percentile_threshold(growth_vals, analysis_cfg["growth_top_decile"])
        grow_lo = percentile_threshold(growth_vals, analysis_cfg["growth_bottom_decile"])

        sec_high_texts = group[group["scores"].apply(lambda x: x["security_axis"] >= sec_hi)]["text"].tolist()
        sec_low_texts = group[group["scores"].apply(lambda x: x["security_axis"] <= sec_lo)]["text"].tolist()
        grow_high_texts = group[group["scores"].apply(lambda x: x["growth_axis"] >= grow_hi)]["text"].tolist()
        grow_low_texts = group[group["scores"].apply(lambda x: x["growth_axis"] <= grow_lo)]["text"].tolist()

        sec_df = compute_keyness(sec_high_texts, sec_low_texts, n_min, n_max, method, alpha, top_n)
        grow_df = compute_keyness(grow_high_texts, grow_low_texts, n_min, n_max, method, alpha, top_n)
        sec_df.to_csv(output_dir / f"keyness_security_{year}.csv", index=False, encoding="utf-8")
        grow_df.to_csv(output_dir / f"keyness_growth_{year}.csv", index=False, encoding="utf-8")

    period_a = df[df["date"] <= "2017-12-31"]["text"].tolist()
    period_b = df[df["date"] >= "2022-01-01"]["text"].tolist()
    if period_a and period_b:
        sec_period = compute_keyness(period_a, period_b, n_min, n_max, method, alpha, top_n)
        sec_period.to_csv(output_dir / "keyness_security_period.csv", index=False, encoding="utf-8")
        grow_period = compute_keyness(period_a, period_b, n_min, n_max, method, alpha, top_n)
        grow_period.to_csv(output_dir / "keyness_growth_period.csv", index=False, encoding="utf-8")


def run_trends(rows: list[dict]) -> None:
    trend_df = run_trend(rows)
    output_dir = Path("outputs/tables")
    output_dir.mkdir(parents=True, exist_ok=True)
    trend_df.to_csv(output_dir / "q1_trend_quarterly.csv", index=False, encoding="utf-8")

    fig, ax = plt.subplots(figsize=(10, 5))
    mfa = trend_df[trend_df["source_type"] == "mfa_presser"]
    ax.plot(mfa["bin"], mfa["security_mean"], label="security")
    ax.plot(mfa["bin"], mfa["growth_mean"], label="growth")
    ax.set_xlabel("Quarter")
    ax.set_ylabel("Mean score")
    ax.legend()
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig_path = Path("outputs/figures") / "q1_trend_quarterly.png"
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)


def run_coupling_tests(rows: list[dict]) -> None:
    coupling_df = run_coupling(rows)
    output_dir = Path("outputs/tables")
    output_dir.mkdir(parents=True, exist_ok=True)
    coupling_df.to_csv(output_dir / "q2_coupling_quarterly.csv", index=False, encoding="utf-8")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(coupling_df["bin"], coupling_df["corr_outward_security"], label="outward-security")
    ax.plot(coupling_df["bin"], coupling_df["corr_outward_growth"], label="outward-growth")
    ax.set_xlabel("Quarter")
    ax.set_ylabel("Correlation")
    ax.legend()
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig_path = Path("outputs/figures") / "q2_coupling_quarterly.png"
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)


def run_slogans(rows: list[dict], analysis_cfg: dict) -> None:
    output_dir = Path("outputs/tables")
    output_dir.mkdir(parents=True, exist_ok=True)
    stoplist = load_stoplist(analysis_cfg["slogans"]["stoplist_path"])
    curated = load_curated(analysis_cfg["slogans"]["curated_path"])
    party_texts = [r["text"] for r in rows if r["source_type"] == "party_report"]
    candidates = extract_candidates(
        party_texts,
        analysis_cfg["slogans"]["min_len"],
        analysis_cfg["slogans"]["max_len"],
        stoplist,
        analysis_cfg["slogans"]["top_n"],
    )
    candidates.to_csv(output_dir / "slogans_candidates.csv", index=False, encoding="utf-8")
    slogans = curated if curated else candidates["slogan"].head(50).tolist()
    metrics = slogan_metrics(rows, slogans)
    metrics.to_csv(output_dir / "slogans_quarterly.csv", index=False, encoding="utf-8")


def run_elasticity(rows: list[dict], analysis_cfg: dict) -> None:
    embeddings_path = Path("data/embeddings")
    if not embeddings_path.exists():
        return
    all_embeddings = []
    bin_map = {}
    segment_index_map = {}
    for doc_id in {r["doc_id"] for r in rows}:
        cache = embeddings_path / f"{doc_id}.npz"
        if not cache.exists():
            continue
        data = np.load(cache, allow_pickle=True)
        emb = data["embeddings"].astype(np.float32)
        start_idx = len(all_embeddings)
        all_embeddings.append(emb)
        doc_rows = [r for r in rows if r["doc_id"] == doc_id and r["segment_type"] != "heading"]
        for idx, row in enumerate(doc_rows):
            global_idx = start_idx + idx
            bin_map[global_idx] = row["date"]
            segment_index_map[row["segment_id"]] = global_idx
    if not all_embeddings:
        return
    matrix = np.vstack(all_embeddings)
    labels = cluster_embeddings(matrix, analysis_cfg["cluster"]["k"], analysis_cfg["cluster"]["random_state"])

    stoplist = load_stoplist(analysis_cfg["slogans"]["stoplist_path"])
    curated = load_curated(analysis_cfg["slogans"]["curated_path"])
    party_texts = [r["text"] for r in rows if r["source_type"] == "party_report"]
    candidates = extract_candidates(
        party_texts,
        analysis_cfg["slogans"]["min_len"],
        analysis_cfg["slogans"]["max_len"],
        stoplist,
        analysis_cfg["slogans"]["top_n"],
    )
    slogans = curated if curated else candidates["slogan"].head(50).tolist()

    slogan_map = slogan_presence(rows, slogans)
    slogan_indices = {
        slogan: [segment_index_map[seg_id] for seg_id in ids if seg_id in segment_index_map]
        for slogan, ids in slogan_map.items()
    }
    summary, series = slogan_entropy(slogan_indices, labels, bin_map)
    summary.to_csv(Path("outputs/tables") / "slogan_elasticity.csv", index=False, encoding="utf-8")
    series.to_csv(Path("outputs/tables") / "slogan_entropy_timeseries.csv", index=False, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--analysis-start", default=None)
    parser.add_argument("--analysis-end", default=None)
    args = parser.parse_args()
    cfg = load_config_bundle(args.config_dir)
    rows = jsonl_read(Path("data/segments") / "segments_scored.jsonl")
    run_keyness(rows, cfg["analysis"])
    run_trends(rows)
    run_coupling_tests(rows)
    run_slogans(rows, cfg["analysis"])
    run_elasticity(rows, cfg["analysis"])


if __name__ == "__main__":
    main()
