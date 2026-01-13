from __future__ import annotations

import re
from urllib.parse import urljoin
from pathlib import Path
from typing import Any, Dict, List

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
        docs = []
        seen_urls = set()
        for listing in self.config.get("listing_bases", []):
            base = listing["base"]
            first_page = listing["first_page"]
            page_pattern = listing["page_pattern"]
            empty_pages = 0
            for page in range(0, 200):
                page_name = first_page if page == 0 else page_pattern.format(page=page)
                page_url = urljoin(base, page_name)
                try:
                    html = self.fetch(page_url, force=False)
                except requests.RequestException:
                    break
                soup = BeautifulSoup(html, "lxml")
                page_docs = 0
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    text = normalize_ws(link.get_text(" "))
                    doc_date = self._infer_date(text, href)
                    if not doc_date:
                        continue
                    if not (start <= doc_date <= end):
                        continue
                    abs_url = urljoin(base, href)
                    if abs_url in seen_urls:
                        continue
                    seen_urls.add(abs_url)
                    docs.append(
                        {
                            "title": text,
                            "date": doc_date,
                            "language": self.config.get("language", "zh"),
                            "urls": [abs_url],
                            "canonical_url": abs_url,
                        }
                    )
                    page_docs += 1
                if page_docs == 0:
                    empty_pages += 1
                else:
                    empty_pages = 0
                if empty_pages >= 2:
                    break
        return docs

    def _infer_date(self, text: str, href: str) -> str:
        match = re.search(r"(20\d{2})[-./](\d{1,2})[-./](\d{1,2})", text + " " + href)
        if not match:
            return ""
        y, m, d = match.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"

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
