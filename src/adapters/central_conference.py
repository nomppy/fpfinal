from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

from src.utils import ensure_dir, normalize_ws, sha1_text


class CentralConferenceAdapter:
    def __init__(self, config: Dict[str, Any], cache_dir: Path):
        self.config = config
        self.cache_dir = cache_dir
        ensure_dir(cache_dir)

    def list_doc_urls(self, date_range: tuple[str, str]) -> List[Dict[str, Any]]:
        start, end = date_range
        docs = []
        for item in self.config.get("docs", []):
            if start <= item["date"] <= end:
                urls = [item["canonical_url"]] + item.get("mirrors", [])
                docs.append(
                    {
                        "doc_id": item.get("doc_id"),
                        "title": item.get("title", ""),
                        "date": item.get("date", ""),
                        "language": item.get("language", self.config.get("language", "zh")),
                        "canonical_url": item.get("canonical_url"),
                        "urls": urls,
                    }
                )
        return docs

    def fetch(self, url: str, force: bool = False) -> str:
        cache_path = self.cache_dir / f"{sha1_text(url)}.html"
        if cache_path.exists() and not force:
            return cache_path.read_text(encoding="utf-8")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        html = resp.text
        cache_path.write_text(html, encoding="utf-8")
        return html

    def parse(self, raw: str) -> Dict[str, Any]:
        soup = BeautifulSoup(raw, "lxml")
        title = normalize_ws(soup.title.get_text()) if soup.title else ""
        paragraphs = [normalize_ws(p.get_text(" ")) for p in soup.find_all("p") if normalize_ws(p.get_text(" "))]
        text = "\n".join(paragraphs)
        return {
            "title": title,
            "date": "",
            "text": text,
            "metadata": {},
        }

    def segment(self, text: str) -> List[Dict[str, Any]]:
        return [
            {
                "segment_index": idx,
                "segment_type": "body",
                "text": para,
            }
            for idx, para in enumerate([p for p in text.split("\n") if p.strip()])
        ]

    def normalize(self, segment_text: str) -> str:
        return normalize_ws(segment_text)
