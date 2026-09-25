from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        model_name = model_name.strip()
        if not model_name:
            raise ValueError("Embedding model name must not be empty.")
        self.model_name = model_name
        self.model = _load_model(model_name)

    @staticmethod
    def _validate_texts(texts: list[str]) -> list[str]:
        cleaned: list[str] = []
        for index, text in enumerate(texts):
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"Embedding text at position {index} must be a non-empty string.")
            cleaned.append(text.strip())
        return cleaned

    @property
    def dimension(self) -> int:
        get_dimension = getattr(self.model, "get_embedding_dimension", None)
        dimension = get_dimension() if get_dimension else self.model.get_sentence_embedding_dimension()
        if dimension is None:
            raise RuntimeError(f"Cannot determine embedding dimension for {self.model_name}.")
        return int(dimension)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        cleaned = self._validate_texts(texts)
        embeddings = self.model.encode(
            cleaned,
            batch_size=32,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        cleaned = self._validate_texts([text])
        embedding = self.model.encode(
            cleaned,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embedding[0].tolist()
