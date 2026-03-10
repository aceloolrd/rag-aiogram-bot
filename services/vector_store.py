from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np


@dataclass
class VectorStore:
    """Минимальный векторный стор без FAISS.

    Почему так:
    - кроссплатформенно (Windows/Linux/macOS)
    - сохраняется “честно” в .npy + .jsonl
    - достаточно быстро для статей/документов обычного размера
    """
    vectors: np.ndarray  # shape: (n, d), float32, нормализованные
    chunks: List[Dict[str, Any]]  # список метаданных/текста по индексу строки

    @property
    def size(self) -> int:
        return int(self.vectors.shape[0]) if self.vectors is not None else 0

    def save(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)

        np.save(folder / "vectors.npy", self.vectors.astype(np.float32), allow_pickle=False)

        with (folder / "chunks.jsonl").open("w", encoding="utf-8") as f:
            for item in self.chunks:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        # сохранение метаданных
        meta = {"size": self.size, "dim": int(self.vectors.shape[1])}
        (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def load(folder: Path) -> "VectorStore":
        vectors_path = folder / "vectors.npy"
        chunks_path = folder / "chunks.jsonl"

        if not vectors_path.exists() or not chunks_path.exists():
            raise FileNotFoundError("Индекс не найден (vectors.npy/chunks.jsonl отсутствуют).")

        vectors = np.load(vectors_path, allow_pickle=False).astype(np.float32)

        chunks: List[Dict[str, Any]] = []
        with chunks_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                chunks.append(json.loads(line))

        if len(chunks) != vectors.shape[0]:
            raise ValueError("Повреждён индекс: количество векторов не совпадает с количеством чанков.")

        return VectorStore(vectors=vectors, chunks=chunks)

    def search(self, query_vec: np.ndarray, k: int = 4) -> List[Tuple[Dict[str, Any], float]]:
        """Возвращает top-k чанков и score (косинус, т.к. всё нормализовано)."""
        if self.size == 0:
            return []

        query_vec = query_vec.astype(np.float32).reshape(1, -1)

        # это одномерный массив (размер n), где для каждого вектора 
        # в индексе посчитано скалярное произведение с query_vec.
        scores = (self.vectors @ query_vec.T).reshape(-1)

        k = max(1, min(k, self.size))
        # быстрый поиск топ-k элементов без полной сортировки всего массива
        top_idx = np.argpartition(-scores, kth=k - 1)[:k]
        top_idx = top_idx[np.argsort(-scores[top_idx])]

        return [(self.chunks[int(i)], float(scores[int(i)])) for i in top_idx]


def l2_normalize(v: np.ndarray) -> np.ndarray:
    v = v.astype(np.float32)
    norms = np.linalg.norm(v, axis=1, keepdims=True) + 1e-12
    return v / norms
