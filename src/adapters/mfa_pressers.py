from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from src.utils import ensure_dir, normalize_ws, sha1_text


QA_Q_RE = re.compile(r"^(问|记者)：?\s*")
QA_A_RE = re.compile(r"^(答|发言人)：?\s*")


class MFAPressersAdapter:
    def __init__(self, config: Dict[str, Any], cache_dir: Path):
        self.config = config
        self.cache_dir = cache_dir
        ensure_dir(cache_dir)

    def list_doc_urls(self, date_range: tuple[str, str]) -> List[Dict[str, Any]]:
        start, end = date_range
        docs: List[Dict[str, Any]] = []
        link_patterns = self.config.get("link_patterns", [])
        seen_urls: set[str] = set()

        index_pages = self.config.get("index_pages", [])
        if index_pages:
            for page in index_pages:
                if str(page.get("year", "")) < start[:4] or str(page.get("year", "")) > end[:4]:
                    continue
                html = self.fetch(page["url"], force=False)
                docs.extend(self._extract_docs(html, page["url"], link_patterns, seen_urls))
        else:
            for base in self.config.get("listing_bases", []):
                for page_url in self._iter_listing_pages(base):
                    html = self.fetch(page_url, force=False, allow_404=True)
                    if not html:
                        break
                    docs.extend(self._extract_docs(html, page_url, link_patterns, seen_urls))

        docs.extend(self.config.get("fallback_urls", []))
        return [d for d in docs if d.get("date") and start <= d["date"] <= end]

    def _infer_date(self, text: str, href: str) -> str:
        match = re.search(r"(20\d{2})[-./](\d{1,2})[-./](\d{1,2})", text + " " + href)
        if not match:
            return ""
        y, m, d = match.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"

    def fetch(self, url: str, force: bool = False, allow_404: bool = False) -> str:
        cache_path = self.cache_dir / f"{sha1_text(url)}.html"
        if cache_path.exists() and not force:
            return cache_path.read_text(encoding="utf-8")
        resp = requests.get(url, timeout=30)
        if allow_404 and resp.status_code == 404:
            return ""
        resp.raise_for_status()
        html = resp.text
        cache_path.write_text(html, encoding="utf-8")
        return html

    def parse(self, raw: str) -> Dict[str, Any]:
        soup = BeautifulSoup(raw, "lxml")
        title = normalize_ws(soup.title.get_text()) if soup.title else ""
        content = soup.get_text("\n")
        text = "\n".join([normalize_ws(line) for line in content.split("\n") if normalize_ws(line)])
        return {
            "title": title,
            "date": "",
            "text": text,
            "metadata": {},
        }

    def segment(self, text: str) -> List[Dict[str, Any]]:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        qa_segments: List[Dict[str, Any]] = []
        if any(QA_Q_RE.match(line) or QA_A_RE.match(line) for line in lines):
            buffer = []
            current_type = None
            idx = 0
            for line in lines:
                if QA_Q_RE.match(line):
                    if buffer and current_type:
                        qa_segments.append({
                            "segment_index": idx,
                            "segment_type": current_type,
                            "text": " ".join(buffer),
                        })
                        idx += 1
                    buffer = [QA_Q_RE.sub("", line).strip()]
                    current_type = "q_turn"
                elif QA_A_RE.match(line):
                    if buffer and current_type:
                        qa_segments.append({
                            "segment_index": idx,
                            "segment_type": current_type,
                            "text": " ".join(buffer),
                        })
                        idx += 1
                    buffer = [QA_A_RE.sub("", line).strip()]
                    current_type = "a_turn"
                else:
                    buffer.append(line)
            if buffer and current_type:
                qa_segments.append({
                    "segment_index": idx,
                    "segment_type": current_type,
                    "text": " ".join(buffer),
                })
        if qa_segments:
            return qa_segments
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

    def _iter_listing_pages(self, base_entry: Dict[str, Any]) -> List[str]:
        base = base_entry["base"]
        first_page = base_entry.get("first_page", "index.shtml")
        page_pattern = base_entry.get("page_pattern", "index_{page}.shtml")
        max_pages = base_entry.get("max_pages") or self.config.get("max_pages", 200)
        return [
            f"{base.rstrip('/')}/{(first_page if page == 0 else page_pattern.format(page=page)).lstrip('/')}"
            for page in range(max_pages)
        ]

    def _extract_docs(
        self,
        html: str,
        page_url: str,
        link_patterns: List[str],
        seen_urls: set[str],
    ) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        docs: List[Dict[str, Any]] = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = normalize_ws(link.get_text(" "))
            abs_url = urljoin(page_url, href)
            if link_patterns and not any(pat in abs_url for pat in link_patterns):
                continue
            date = self._infer_date(text, abs_url)
            if not date:
                continue
            if abs_url in seen_urls:
                continue
            seen_urls.add(abs_url)
            docs.append({
                "title": text,
                "date": date,
                "language": "zh",
                "url": abs_url,
                "canonical_url": abs_url,
            })
        return docs
