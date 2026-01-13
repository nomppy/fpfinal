from __future__ import annotations

from typing import Any, Dict, List

from src.utils import normalize_ws, text_hash


def build_segments(doc_id: str, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for seg in segments:
        seg_text = normalize_ws(seg["text"])
        out.append(
            {
                "segment_id": text_hash(f"{doc_id}-{seg['segment_index']}")[:16],
                "doc_id": doc_id,
                "segment_index": seg["segment_index"],
                "segment_type": seg["segment_type"],
                "text": seg_text,
                "char_len": len(seg_text),
                "embedding_ref": None,
                "scores": {},
                "contains_slogans": [],
            }
        )
    return out


def merge_document(doc: Dict[str, Any], segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    doc_out = dict(doc)
    doc_out["segments"] = segments
    doc_out["clean_text"] = "\n".join(seg["text"] for seg in segments)
    return doc_out

