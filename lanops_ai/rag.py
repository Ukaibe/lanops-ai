import json
import math
from pathlib import Path
from threading import Lock

from langchain_ollama import OllamaEmbeddings

from lanops_ai.config import get_settings


class KnowledgeBase:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.path = Path(self.settings.rag_path)
        self.lock = Lock()
        self.embeddings = OllamaEmbeddings(
            model=self.settings.embedding_model, base_url=self.settings.ollama_url
        )

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def add(self, text: str, source: str) -> int:
        chunks = [
            text[i : i + 1200]
            for i in range(0, len(text), 1000)
            if text[i : i + 1200].strip()
        ]
        vectors = self.embeddings.embed_documents(chunks)
        with self.lock:
            records = self._load()
            records.extend(
                {"text": chunk, "source": source, "vector": vector}
                for chunk, vector in zip(chunks, vectors)
            )
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(records), encoding="utf-8")
        return len(chunks)

    def search(self, query: str, limit: int = 4) -> list[dict]:
        records = self._load()
        if not records:
            return []
        query_vector = self.embeddings.embed_query(query)

        def similarity(record: dict) -> float:
            vector = record["vector"]
            denominator = math.sqrt(sum(x * x for x in vector)) * math.sqrt(
                sum(x * x for x in query_vector)
            )
            return (
                sum(a * b for a, b in zip(vector, query_vector)) / denominator
                if denominator
                else 0.0
            )

        ranked = sorted(records, key=similarity, reverse=True)[: max(1, min(limit, 10))]
        return [
            {"text": row["text"], "source": row["source"], "score": similarity(row)}
            for row in ranked
        ]


knowledge_base = KnowledgeBase()
