from __future__ import annotations

import re
import random
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin

import chardet
import requests
from bs4 import BeautifulSoup

from src.utils import ensure_dir, normalize_ws, sha1_text


QA_Q_RE = re.compile(r"^(?:问|记者(?:问|提问)?)[:：]?\s*")
QA_A_RE = re.compile(r"^(?:答|发言人(?:答)?)[:：]?\s*")


class MFAPressersAdapter:
    def __init__(self, config: Dict[str, Any], cache_dir: Path):
        self.config = config
        self.cache_dir = cache_dir
        self.max_docs = self._normalize_limit(config.get("max_docs"))
        self.max_docs_per_year = self._normalize_limit(config.get("max_docs_per_year"))
        self.sample_years = self._normalize_sample_years(config.get("sample_years"))
        self.sample_strategy = self._normalize_sample_strategy(config.get("sample_strategy", "even"))
        self.sample_seed = self._normalize_sample_seed(config.get("sample_seed"))
        ensure_dir(cache_dir)

    def _normalize_limit(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            value_int = int(value)
        except (TypeError, ValueError):
            return None
        return value_int if value_int > 0 else None

    def _normalize_sample_years(self, value: Any) -> List[str]:
        if not value:
            return []
        years: List[str] = []
        for item in value:
            year = str(item).strip()
            if re.match(r"^20\d{2}$", year):
                years.append(year)
        return sorted(set(years))

    def _normalize_sample_strategy(self, value: Any) -> str:
        strategy = str(value or "even").strip().lower()
        if strategy in {"even", "random"}:
            return strategy
        return "even"

    def _normalize_sample_seed(self, value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def list_doc_urls(self, date_range: tuple[str, str]) -> List[Dict[str, Any]]:
        start, end = date_range
        if self.sample_years:
            start = f"{min(self.sample_years)}-01-01"
            end = f"{max(self.sample_years)}-12-31"
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
                    page_docs = self._extract_docs(html, page_url, link_patterns, seen_urls)
                    docs.extend(page_docs)
                    if self._page_reaches_start(page_docs, start):
                        break

        docs.extend(self.config.get("fallback_urls", []))
        filtered = [d for d in docs if d.get("date") and start <= d["date"] <= end]
        if self.sample_years:
            year_set = set(self.sample_years)
            filtered = [d for d in filtered if d["date"][:4] in year_set]
        if self.max_docs_per_year:
            filtered = self._sample_docs_by_year(filtered, self.max_docs_per_year)
        if self.max_docs:
            filtered.sort(key=lambda d: d.get("date", ""), reverse=True)
            return filtered[: self.max_docs]
        return filtered

    def _infer_date(self, text: str, href: str) -> str:
        haystack = f"{text} {href}"
        match = re.search(r"(20\d{2})[-./](\d{1,2})[-./](\d{1,2})", haystack)
        if not match:
            match = re.search(r"(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日", haystack)
        if not match:
            match = re.search(r"(20\d{2})(\d{2})(\d{2})", haystack)
        if not match:
            return ""
        y, m, d = match.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"

    def _page_reaches_start(self, page_docs: List[Dict[str, Any]], start: str) -> bool:
        if not page_docs:
            return False
        oldest = min(d["date"] for d in page_docs if d.get("date"))
        return oldest < start if oldest else False

    def _sample_docs_by_year(self, docs: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        by_year: Dict[str, List[Dict[str, Any]]] = {}
        for doc in docs:
            year = doc["date"][:4]
            by_year.setdefault(year, []).append(doc)
        sampled: List[Dict[str, Any]] = []
        rng = random.Random(self.sample_seed)
        for year, items in by_year.items():
            items.sort(key=lambda d: d.get("date", ""))
            if len(items) <= limit:
                sampled.extend(items)
                continue
            if limit == 1:
                sampled.append(items[-1])
                continue
            if self.sample_strategy == "random":
                sampled.extend(rng.sample(items, limit))
                continue
            step = (len(items) - 1) / (limit - 1)
            indices = [int(round(i * step)) for i in range(limit)]
            sampled.extend([items[idx] for idx in indices])
        sampled.sort(key=lambda d: d.get("date", ""))
        return sampled

    def fetch(self, url: str, force: bool = False, allow_404: bool = False) -> str:
        cache_path = self.cache_dir / f"{sha1_text(url)}.html"
        if cache_path.exists() and not force:
            return self._read_with_encoding_detection(cache_path)
        resp = requests.get(url, timeout=30)
        if allow_404 and resp.status_code == 404:
            return ""
        resp.raise_for_status()
        detected = chardet.detect(resp.content)
        encoding = detected.get("encoding") or "utf-8"
        try:
            html = resp.content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            html = resp.text
        cache_path.write_text(html, encoding="utf-8")
        return html

    def _read_with_encoding_detection(self, path: Path) -> str:
        raw_bytes = path.read_bytes()
        detected = chardet.detect(raw_bytes)
        encoding = detected.get("encoding") or "utf-8"
        try:
            return raw_bytes.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            return raw_bytes.decode("utf-8", errors="replace")

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
        max_pages = base_entry.get("max_pages") or self.config.get("max_pages", 10)
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
        for link in self._candidate_links(soup):
            href = link.get("href", "")
            abs_url = urljoin(page_url, href)
            if link_patterns and not any(pat in abs_url for pat in link_patterns):
                continue
            date = self._infer_date_from_context(link, abs_url)
            if not date:
                continue
            if abs_url in seen_urls:
                continue
            seen_urls.add(abs_url)
            docs.append({
                "title": normalize_ws(link.get_text(" ")),
                "date": date,
                "language": "zh",
                "url": abs_url,
                "canonical_url": abs_url,
            })
        return docs

    def _candidate_links(self, soup: BeautifulSoup) -> List[Any]:
        links = soup.select("ul.list1 li a[href]")
        if links:
            return links
        links = soup.select(".newsList a[href]")
        if links:
            return links
        return soup.find_all("a", href=True)

    def _infer_date_from_context(self, link: Any, abs_url: str) -> str:
        candidates = []
        text = normalize_ws(link.get_text(" "))
        if text:
            candidates.append(text)
        title_attr = normalize_ws(link.get("title", ""))
        if title_attr:
            candidates.append(title_attr)
        parent = link.find_parent("li") or link.parent
        if parent is not None:
            parent_text = normalize_ws(parent.get_text(" "))
            if parent_text and parent_text not in candidates:
                candidates.append(parent_text)
            for sibling in list(link.previous_siblings) + list(link.next_siblings):
                if getattr(sibling, "get_text", None):
                    sibling_text = normalize_ws(sibling.get_text(" "))
                    if sibling_text and sibling_text not in candidates:
                        candidates.append(sibling_text)
        for candidate in candidates:
            date = self._infer_date(candidate, abs_url)
            if date:
                return date
        return ""
