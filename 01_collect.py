#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from src.adapters.central_conference import CentralConferenceAdapter
from src.adapters.mfa_pressers import MFAPressersAdapter
from src.adapters.party_reports import PartyReportsAdapter
from src.utils import (
    ensure_dir,
    jsonl_write,
    load_config_bundle,
    save_json,
    sha1_text,
)


def collect_docs(config_dir: str, analysis_start: str | None, analysis_end: str | None, force: bool) -> None:
    cfg = load_config_bundle(config_dir)
    sources = cfg["sources"]
    analysis = cfg["analysis"]
    start, end = analysis_start or analysis["analysis_start"], analysis_end or analysis["analysis_end"]
    if analysis.get("sample_mode", False):
        sample_year = str(analysis.get("sample_year", start[:4]))
        start, end = f"{sample_year}-01-01", f"{sample_year}-12-31"
    cache_dir = Path("data/cache")
    raw_dir = ensure_dir(Path("data/raw"))
    parsed_dir = ensure_dir(Path("data/parsed"))

    adapters = [
        PartyReportsAdapter(sources["party_reports"], cache_dir / "party"),
        MFAPressersAdapter(sources["mfa_pressers"], cache_dir / "mfa"),
        CentralConferenceAdapter(sources["central_conferences"], cache_dir / "conference"),
    ]

    docs_out = []
    for adapter in adapters:
        for doc in adapter.list_doc_urls((start, end)):
            urls = doc.get("urls") or [doc["url"]]
            doc_id = doc.get("doc_id") or sha1_text(doc.get("canonical_url", urls[0]))[:16]
            raw_html = None
            used_url = None
            for candidate in urls:
                try:
                    raw_html = adapter.fetch(candidate, force=force)
                    used_url = candidate
                    break
                except Exception as exc:
                    print(f"[collect] Failed to fetch {candidate}: {exc}")
            if raw_html is None:
                continue
            raw_path = raw_dir / f"{doc_id}.html"
            raw_path.write_text(raw_html, encoding="utf-8")
            parsed = adapter.parse(raw_html)
            parsed["title"] = doc.get("title") or parsed.get("title")
            parsed["date"] = doc.get("date") or parsed.get("date")
            parsed["metadata"].update({"source_type": adapter.config["source_type"], "source_org": adapter.config["source_org"]})
            parsed_doc = {
                "doc_id": doc_id,
                "source_type": adapter.config["source_type"],
                "source_org": adapter.config["source_org"],
                "title": parsed["title"],
                "date": parsed["date"],
                "language": doc.get("language", adapter.config.get("language", "zh")),
                "url": used_url or urls[0],
                "canonical_url": doc.get("canonical_url", used_url or urls[0]),
                "raw_path": str(raw_path),
                "clean_text": parsed["text"],
                "segments": [],
            }
            save_json(parsed_dir / f"{doc_id}.json", parsed_doc)
            docs_out.append(parsed_doc)

    jsonl_write(parsed_dir / "docs.jsonl", docs_out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--analysis-start", default=None)
    parser.add_argument("--analysis-end", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    collect_docs(args.config_dir, args.analysis_start, args.analysis_end, args.force)


if __name__ == "__main__":
    main()
