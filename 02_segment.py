#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from src.adapters.party_reports import PartyReportsAdapter
from src.segment import build_segments, merge_document
from src.utils import ensure_utf8, jsonl_read, jsonl_write, load_config_bundle, load_json, save_json


def segment_docs(config_dir: str) -> None:
    cfg = load_config_bundle(config_dir)
    sources = cfg["sources"]
    cache_dir = Path("data/cache")
    parsed_dir = Path("data/parsed")
    segments_dir = Path("data/segments")
    segments_dir.mkdir(parents=True, exist_ok=True)

    adapters = {
        "party_report": PartyReportsAdapter(sources["party_reports"], cache_dir / "party"),
        # "mfa_presser": MFAPressersAdapter(sources["mfa_pressers"], cache_dir / "mfa"),
        # "central_conference": CentralConferenceAdapter(sources["central_conferences"], cache_dir / "conference"),
    }

    docs = jsonl_read(parsed_dir / "docs.jsonl")
    out_docs = []
    for doc in docs:
        if doc["source_type"] not in adapters:
            continue
        adapter = adapters[doc["source_type"]]
        raw_bytes = Path(doc["raw_path"]).read_bytes()
        raw_html = ensure_utf8(raw_bytes)
        parsed = adapter.parse(raw_html)
        segments = adapter.segment(parsed["text"])
        segments = [
            {**seg, "text": adapter.normalize(seg["text"])}
            for seg in segments
        ]
        seg_rows = build_segments(doc["doc_id"], segments)
        merged = merge_document(doc, seg_rows)
        save_json(segments_dir / f"{doc['doc_id']}.json", merged)
        out_docs.append(merged)

    jsonl_write(segments_dir / "segments.jsonl", out_docs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--analysis-start", default=None)
    parser.add_argument("--analysis-end", default=None)
    args = parser.parse_args()
    segment_docs(args.config_dir)


if __name__ == "__main__":
    main()
