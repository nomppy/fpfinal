from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import chardet
import requests
from bs4 import BeautifulSoup

from src.utils import ensure_dir, normalize_ws, sha1_text


class PartyReportsAdapter:
    def __init__(self, config: Dict[str, Any], cache_dir: Path):
        self.config = config
        self.cache_dir = cache_dir
        ensure_dir(cache_dir)

    def list_doc_urls(self, date_range: tuple[str, str]) -> List[Dict[str, Any]]:
        start, end = date_range
        docs = []
        for item in self._normalize_docs():
            if start <= item["date"] <= end:
                docs.append(item)
        return docs

    def _normalize_docs(self) -> List[Dict[str, Any]]:
        raw_docs = self.config.get("urls") or self.config.get("docs") or []
        docs: List[Dict[str, Any]] = []
        for item in raw_docs:
            url = item.get("url")
            canonical_url = item.get("canonical_url")
            mirrors = item.get("mirrors") or []
            if not url:
                url = canonical_url or (mirrors[0] if mirrors else "")
            if not canonical_url:
                canonical_url = url
            if not url:
                continue
            doc = dict(item)
            doc["url"] = url
            doc["canonical_url"] = canonical_url
            docs.append(doc)
        return docs

    def fetch(self, url: str, force: bool = False) -> str:
        cache_path = self.cache_dir / f"{sha1_text(url)}.html"
        if cache_path.exists() and not force:
            return self._read_with_encoding_detection(cache_path)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        # Detect encoding from response content
        detected = chardet.detect(resp.content)
        encoding = detected.get('encoding') or 'utf-8'
        try:
            html = resp.content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            html = resp.text
        cache_path.write_text(html, encoding="utf-8")
        return html

    def _read_with_encoding_detection(self, path: Path) -> str:
        """Read HTML file, detecting encoding from content."""
        raw_bytes = path.read_bytes()
        detected = chardet.detect(raw_bytes)
        encoding = detected.get('encoding') or 'utf-8'
        try:
            return raw_bytes.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            return raw_bytes.decode('utf-8', errors='replace')

    def parse(self, raw: str) -> Dict[str, Any]:
        soup = BeautifulSoup(raw, "lxml")
        title = normalize_ws(soup.title.get_text()) if soup.title else ""
        paragraphs = []
        for el in soup.find_all(["p", "h1", "h2", "h3"]):
            text = normalize_ws(el.get_text(" "))
            if text:
                paragraphs.append(text)
        text = "\n".join(paragraphs)
        return {
            "title": title,
            "date": "",
            "text": text,
            "metadata": {},
        }

    def segment(self, text: str) -> List[Dict[str, Any]]:
        segments = []
        for idx, para in enumerate([p for p in text.split("\n") if p.strip()]):
            seg_type = "body"
            if re.match(r"^第[一二三四五六七八九十]+", para) or len(para) < 20:
                seg_type = "heading"
            segments.append({
                "segment_index": idx,
                "segment_type": seg_type,
                "text": para,
            })
        return segments

    def normalize(self, segment_text: str) -> str:
        return normalize_ws(segment_text)
