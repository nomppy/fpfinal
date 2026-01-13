from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from src.tests.trend import quarterly_bin

CJK_RE = re.compile(r"[\u4e00-\u9fff]+")


def cjk_ngrams(text: str, n_min: int, n_max: int) -> Iterable[str]:
    for match in CJK_RE.finditer(text):
        chunk = match.group(0)
        for n in range(n_min, n_max + 1):
            for i in range(0, len(chunk) - n + 1):
                yield chunk[i : i + n]


def extract_candidates(texts: List[str], n_min: int, n_max: int, stoplist: set[str], top_n: int) -> pd.DataFrame:
    counter = Counter()
    for text in texts:
        counter.update(cjk_ngrams(text, n_min, n_max))
    for stop in stoplist:
        counter.pop(stop, None)
    ranked = counter.most_common(top_n)
    return pd.DataFrame(ranked, columns=["slogan", "frequency"])


def _is_mfa_source(source_type: str) -> bool:
    return source_type in {"mfa_presser", "mfa_pressers"}


def slogan_metrics(rows: List[Dict[str, any]], slogans: List[str]) -> pd.DataFrame:
    slogans = [s for s in slogans if s]
    records = []
    for row in rows:
        bin_id = quarterly_bin(row["date"]) if _is_mfa_source(row["source_type"]) else row["date"]
        for slogan in slogans:
            count = row["text"].count(slogan)
            if count:
                records.append(
                    {
                        "bin": bin_id,
                        "source_type": row["source_type"],
                        "slogan": slogan,
                        "count": count,
                        "char_len": row["char_len"],
                        "doc_id": row["doc_id"],
                    }
                )
    if not records:
        return pd.DataFrame(columns=["bin", "source_type", "slogan", "freq_per_10k", "doc_dispersion"])
    df = pd.DataFrame(records)
    grouped = df.groupby(["bin", "source_type", "slogan"])
    rows_out = []
    for (bin_id, source_type, slogan), group in grouped:
        total_chars = group["char_len"].sum()
        freq = (group["count"].sum() / total_chars) * 10000 if total_chars else 0.0
        doc_dispersion = group["doc_id"].nunique()
        rows_out.append(
            {
                "bin": bin_id,
                "source_type": source_type,
                "slogan": slogan,
                "freq_per_10k": freq,
                "doc_dispersion": int(doc_dispersion),
            }
        )
    return pd.DataFrame(rows_out)


def slogan_presence(rows: List[Dict[str, any]], slogans: List[str]) -> Dict[str, List[str]]:
    mapping = defaultdict(list)
    for row in rows:
        for slogan in slogans:
            if slogan and slogan in row["text"]:
                mapping[slogan].append(row["segment_id"])
    return mapping


def entropy_from_counts(counts: List[int]) -> float:
    total = sum(counts)
    if total == 0:
        return 0.0
    ent = 0.0
    for c in counts:
        p = c / total
        ent -= p * math.log(p + 1e-12)
    return ent
