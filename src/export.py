from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from src.tests.trend import quarterly_bin


def build_excerpt_bank(rows: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
    records = []
    for row in rows:
        if not row["scores"].get("is_outward"):
            continue
        bin_id = quarterly_bin(row["date"]) if row["source_type"] == "mfa_presser" else row["date"]
        records.append({"bin": bin_id, **row})
    df = pd.DataFrame(records)
    if df.empty:
        return []
    df["security_axis"] = df["scores"].apply(lambda x: x.get("security_axis", 0.0))
    df["outward_axis"] = df["scores"].apply(lambda x: x.get("outward_axis", 0.0))
    output = []
    for bin_id, group in df.groupby("bin"):
        top_sec = group.sort_values("security_axis", ascending=False).head(top_n)
        bottom_sec = group.sort_values("security_axis", ascending=True).head(top_n)
        top_slogan = group.sort_values("outward_axis", ascending=False).head(top_n)
        for label, subset in [("top_security", top_sec), ("bottom_security", bottom_sec), ("top_slogan", top_slogan)]:
            for _, row in subset.iterrows():
                output.append(
                    {
                        "bin": bin_id,
                        "label": label,
                        "doc_id": row["doc_id"],
                        "date": row["date"],
                        "source_type": row["source_type"],
                        "title": row["title"],
                        "url": row["url"],
                        "text": row["text"],
                        "scores": row["scores"],
                    }
                )
    return output
