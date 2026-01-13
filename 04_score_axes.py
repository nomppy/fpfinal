#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from src.axes import build_axis_vectors, score_segments
from src.embed import EmbeddingEngine
from src.outward_filter import compute_year_thresholds, mark_outward
from src.utils import jsonl_read, jsonl_write, load_config_bundle


def score_axes(config_dir: str, force: bool) -> None:
    cfg = load_config_bundle(config_dir)
    axes_cfg = cfg["axes"]
    models_cfg = cfg["models"]
    embedder = EmbeddingEngine(models_cfg["embedding"], Path("data/embeddings"))
    docs = jsonl_read(Path("data/segments") / "segments_embedded.jsonl")
    axes = build_axis_vectors(axes_cfg, embedder)

    flat_rows = []
    for doc in docs:
        segments = doc["segments"]
        embed_targets = [seg for seg in segments if seg["segment_type"] != "heading"]
        if embed_targets:
            embeddings = embedder.embed_segments(doc["doc_id"], embed_targets, force=force)
            scores = score_segments(embeddings, axes)
        else:
            scores = {"security_axis": [], "growth_axis": [], "outward_axis": []}
        target_iter = iter(range(len(embed_targets))) if embed_targets else iter([])
        for seg in segments:
            if seg["segment_type"] == "heading":
                seg_scores = {"security_axis": 0.0, "growth_axis": 0.0, "outward_axis": 0.0}
            else:
                idx = next(target_iter)
                seg_scores = {
                    "security_axis": float(scores["security_axis"][idx]),
                    "growth_axis": float(scores["growth_axis"][idx]),
                    "outward_axis": float(scores["outward_axis"][idx]),
                }
            seg["scores"].update(seg_scores)
            flat_rows.append(
                {
                    "segment_id": seg["segment_id"],
                    "doc_id": doc["doc_id"],
                    "title": doc["title"],
                    "date": doc["date"],
                    "source_type": doc["source_type"],
                    "source_org": doc["source_org"],
                    "url": doc["url"],
                    "text": seg["text"],
                    "segment_type": seg["segment_type"],
                    "char_len": seg["char_len"],
                    "scores": seg["scores"],
                }
            )
        doc["segments"] = segments

    thresholds = compute_year_thresholds(flat_rows, cfg["analysis"]["outward_percentile"])
    mark_outward(flat_rows, thresholds)

    jsonl_write(Path("data/segments") / "segments_scored.jsonl", flat_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--analysis-start", default=None)
    parser.add_argument("--analysis-end", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    score_axes(args.config_dir, args.force)


if __name__ == "__main__":
    main()
