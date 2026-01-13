from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer

from src.utils import ensure_dir, sha1_text


class EmbeddingEngine:
    def __init__(self, model_cfg: Dict[str, Any], cache_dir: Path):
        self.model_cfg = model_cfg
        self.cache_dir = ensure_dir(cache_dir)
        self.model = SentenceTransformer(model_cfg["model_name"], device=model_cfg["device"])
        self.batch_size = model_cfg["batch_size"]
        self.max_length = model_cfg["max_length"]
        self.cache_mode = model_cfg["cache_mode"]
        self.embedding_dtype = model_cfg.get("embedding_dtype", "float16")

    def _cache_path(self, doc_id: str) -> Path:
        return self.cache_dir / f"{doc_id}.npz"

    def load_cache(self, doc_id: str) -> Dict[str, Any] | None:
        path = self._cache_path(doc_id)
        if not path.exists():
            return None
        data = np.load(path, allow_pickle=True)
        return {
            "segment_ids": data["segment_ids"].tolist(),
            "embeddings": data["embeddings"],
        }

    def save_cache(self, doc_id: str, segment_ids: List[str], embeddings: np.ndarray) -> None:
        path = self._cache_path(doc_id)
        np.savez_compressed(path, segment_ids=np.array(segment_ids), embeddings=embeddings)

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings

    def embed_segments(self, doc_id: str, segments: List[Dict[str, Any]], force: bool = False) -> np.ndarray:
        if self.cache_mode == "embeddings" and not force:
            cached = self.load_cache(doc_id)
            if cached and cached["segment_ids"] == [s["segment_id"] for s in segments]:
                return cached["embeddings"]
        texts = [s["text"] for s in segments]
        embeddings = self.embed_texts(texts)
        if self.embedding_dtype == "float16":
            embeddings = embeddings.astype(np.float16)
        if self.cache_mode == "embeddings":
            self.save_cache(doc_id, [s["segment_id"] for s in segments], embeddings)
        return embeddings

    def embedding_ref(self, text: str) -> str:
        return sha1_text(text)[:16]

