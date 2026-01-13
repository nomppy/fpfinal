import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List

import chardet
import yaml


def load_yaml(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def jsonl_write(path: str | Path, rows: Iterable[Dict[str, Any]]) -> None:
    ensure_dir(Path(path).parent)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def jsonl_read(path: str | Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def save_json(path: str | Path, data: Dict[str, Any]) -> None:
    ensure_dir(Path(path).parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def within_range(date_str: str, start: str, end: str) -> bool:
    return start <= date_str <= end


def chunked(items: List[Any], size: int) -> Iterable[List[Any]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def get_analysis_range(args, analysis_cfg: Dict[str, Any]) -> tuple[str, str]:
    start = args.analysis_start or analysis_cfg["analysis_start"]
    end = args.analysis_end or analysis_cfg["analysis_end"]
    return start, end


def is_sample_mode(args, analysis_cfg: Dict[str, Any]) -> bool:
    return bool(args.sample_mode or analysis_cfg.get("sample_mode", False))


def sample_filter(docs: List[Dict[str, Any]], analysis_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not analysis_cfg.get("sample_mode", False):
        return docs
    year = str(analysis_cfg.get("sample_year", "2017"))
    return [doc for doc in docs if doc["date"].startswith(year)]


def text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def safe_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    return d[key] if key in d else default


def normalize_ws(text: str) -> str:
    return " ".join(text.split())


def load_stoplist(path: str | Path) -> set[str]:
    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip() and not line.strip().startswith("#"))


def load_curated(path: str | Path) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]


def ensure_utf8(data: str | bytes) -> str:
    """Return a UTF-8 string, detecting encoding when given bytes."""
    if isinstance(data, bytes):
        detected = chardet.detect(data)
        encoding = detected.get("encoding") or "utf-8"
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            return data.decode("utf-8", errors="replace")
    if isinstance(data, str):
        return data
    return str(data)


def list_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    if not Path(path).exists():
        return []
    return jsonl_read(path)


def load_config_bundle(config_dir: str) -> Dict[str, Dict[str, Any]]:
    return {
        "sources": load_yaml(Path(config_dir) / "sources.yaml"),
        "analysis": load_yaml(Path(config_dir) / "analysis.yaml"),
        "models": load_yaml(Path(config_dir) / "models.yaml"),
        "axes": load_yaml(Path(config_dir) / "axes.yaml"),
    }

