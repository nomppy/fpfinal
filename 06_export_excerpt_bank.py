#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from src.export import build_excerpt_bank
from src.utils import jsonl_read, jsonl_write


def export_excerpt_bank() -> None:
    rows = jsonl_read(Path("data/segments") / "segments_scored.jsonl")
    excerpt_rows = build_excerpt_bank(rows)
    jsonl_write(Path("outputs/excerpts") / "excerpt_bank.jsonl", excerpt_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--analysis-start", default=None)
    parser.add_argument("--analysis-end", default=None)
    args = parser.parse_args()
    export_excerpt_bank()


if __name__ == "__main__":
    main()
