#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from src.embed import EmbeddingEngine
from src.utils import jsonl_read, jsonl_write, load_config_bundle, save_json


def embed_segments(config_dir: str, force: bool) -> None:
    cfg = load_config_bundle(config_dir)
    models = cfg["models"]
    embedder = EmbeddingEngine(models["embedding"], Path("data/embeddings"))
    segments_dir = Path("data/segments")
    docs = jsonl_read(segments_dir / "segments.jsonl")
    out_docs = []
    for doc in docs:
        segments = doc["segments"]
        embed_targets = [seg for seg in segments if seg["segment_type"] != "heading"]
        if embed_targets:
            embeddings = embedder.embed_segments(doc["doc_id"], embed_targets, force=force)
            for seg in embed_targets:
                seg["embedding_ref"] = embedder.embedding_ref(seg["text"])
        for seg in segments:
            if seg["segment_type"] == "heading":
                seg["embedding_ref"] = None
        doc["segments"] = segments
        save_json(segments_dir / f"{doc['doc_id']}.json", doc)
        out_docs.append(doc)
    jsonl_write(segments_dir / "segments_embedded.jsonl", out_docs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--analysis-start", default=None)
    parser.add_argument("--analysis-end", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    embed_segments(args.config_dir, args.force)


if __name__ == "__main__":
    main()
