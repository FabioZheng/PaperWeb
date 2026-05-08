from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    db_path: str
    vector_store_path: str
    result_store_path: str
    usage_db_path: str


def build_runtime_paths(db_path: str, usage_db_path: str = "data/llm_usage.sqlite") -> RuntimePaths:
    db_file = Path(db_path)
    stem = db_file.stem
    base_dir = db_file.parent
    vector_store_path = str(base_dir / f"{stem}.vector_store.json")
    result_store_path = str(base_dir / f"{stem}.result_store.json")
    return RuntimePaths(
        db_path=str(db_file),
        vector_store_path=vector_store_path,
        result_store_path=result_store_path,
        usage_db_path=usage_db_path,
    )
