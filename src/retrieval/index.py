from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
import pandas as pd

from core.config import Settings
from core.utils import read_json, safe_slug, write_json
from retrieval.embeddings import MiniLMEmbeddings


REQUIRED_DOCUMENT_COLUMNS = {
    "paper_id",
    "title",
    "text_for_embedding",
    "published",
    "authors_joined",
    "categories_joined",
    "summary",
    "abs_url",
    "pdf_url",
}


@dataclass(frozen=True)
class SearchResult:
    paper_id: str
    title: str
    score: float
    content: str
    metadata: dict[str, Any]


class LocalEmbeddingIndex:
    def __init__(
        self,
        settings: Settings,
        collection_name: str,
        documents: list[dict[str, Any]],
        persist_path: Path,
    ):
        self.settings = settings
        self.collection_name = collection_name
        self.documents = documents
        self.persist_path = persist_path
        self.embedding_backend = "chroma"
        self.embedding_model = MiniLMEmbeddings(settings.embedding_model)
        self.client = chromadb.PersistentClient(path=str(persist_path))
        try:
            self.collection = self.client.get_collection(name=collection_name)
        except Exception as exc:
            raise FileNotFoundError(
                f"Chroma collection '{collection_name}' was not found at {persist_path}. "
                "Build the index before loading or searching it."
            ) from exc
        self.documents_by_paper_id = {document["paper_id"].lower(): document for document in documents}
        self.documents_by_title = {document["title"].lower(): document for document in documents}

    @staticmethod
    def _build_documents(df: pd.DataFrame) -> list[dict[str, Any]]:
        missing_columns = sorted(REQUIRED_DOCUMENT_COLUMNS - set(df.columns))
        if missing_columns:
            raise ValueError(f"Cannot build vector index; missing columns: {', '.join(missing_columns)}")
        if df.empty:
            raise ValueError("Cannot build vector index from an empty dataframe.")

        records = df.to_dict(orient="records")
        documents: list[dict[str, Any]] = []
        seen_paper_ids: set[str] = set()
        for index, row in enumerate(records):
            paper_id = str(row["paper_id"]).strip()
            title = str(row["title"]).strip()
            content = str(row["text_for_embedding"]).strip()
            if not paper_id or not title or not content:
                raise ValueError(f"Row {index} has an empty paper_id, title, or text_for_embedding.")

            normalized_paper_id = paper_id.lower()
            if normalized_paper_id in seen_paper_ids:
                raise ValueError(f"Duplicate paper_id cannot be indexed: {paper_id}")
            seen_paper_ids.add(normalized_paper_id)

            def metadata_text(column: str) -> str:
                value = row[column]
                return "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value)

            documents.append(
                {
                    "record_id": f"{paper_id}::{index}",
                    "paper_id": paper_id,
                    "title": title,
                    "content": content,
                    "metadata": {
                        "paper_id": paper_id,
                        "title": title,
                        "published": metadata_text("published"),
                        "authors_joined": metadata_text("authors_joined"),
                        "categories_joined": metadata_text("categories_joined"),
                        "summary": metadata_text("summary"),
                        "abs_url": metadata_text("abs_url"),
                        "pdf_url": metadata_text("pdf_url"),
                    },
                }
            )
        return documents

    @staticmethod
    def _derive_collection_name(settings: Settings, embeddings_output_path: Path | None) -> str:
        if embeddings_output_path is None:
            return settings.baseline_collection_name

        name_map = {
            settings.paths.embeddings_json.resolve(): settings.baseline_collection_name,
            settings.paths.corrupted_embeddings_json.resolve(): settings.corrupted_collection_name,
            settings.paths.repaired_embeddings_json.resolve(): settings.repaired_collection_name,
        }
        resolved_path = embeddings_output_path.resolve()
        if resolved_path in name_map:
            return name_map[resolved_path]
        return safe_slug(embeddings_output_path.stem)

    @classmethod
    def build(
        cls,
        df: pd.DataFrame,
        settings: Settings,
        embeddings_output_path: Path | None = None,
    ) -> "LocalEmbeddingIndex":
        collection_name = cls._derive_collection_name(settings, embeddings_output_path)
        documents = cls._build_documents(df)
        persist_path = settings.paths.chroma_dir
        persist_path.mkdir(parents=True, exist_ok=True)

        embedding_model = MiniLMEmbeddings(settings.embedding_model)
        client = chromadb.PersistentClient(path=str(persist_path))
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            pass
        collection = client.create_collection(
            name=collection_name,
            configuration={"hnsw": {"space": "cosine"}},
        )
        embeddings = embedding_model.embed_documents([document["content"] for document in documents])
        if len(embeddings) != len(documents):
            raise RuntimeError("Embedding backend returned a different number of vectors than documents.")
        collection.add(
            ids=[document["record_id"] for document in documents],
            embeddings=embeddings,
            documents=[document["content"] for document in documents],
            metadatas=[document["metadata"] for document in documents],
        )

        manifest_path = embeddings_output_path or settings.paths.embeddings_json
        try:
            portable_persist_path = persist_path.resolve().relative_to(settings.paths.project_dir.resolve())
        except ValueError:
            portable_persist_path = persist_path.resolve()
        write_json(
            manifest_path,
            {
                "schema_version": 1,
                "backend": "chroma",
                "embedding_model": settings.embedding_model,
                "embedding_dimension": embedding_model.dimension,
                "document_count": len(documents),
                "persist_path": portable_persist_path.as_posix(),
                "collection_name": collection_name,
                "documents": documents,
            },
        )
        return cls(
            settings=settings,
            collection_name=collection_name,
            documents=documents,
            persist_path=persist_path,
        )

    @classmethod
    def load(cls, settings: Settings, embeddings_path: Path | None = None) -> "LocalEmbeddingIndex":
        payload = read_json(embeddings_path or settings.paths.embeddings_json)
        required_keys = {"collection_name", "documents", "persist_path"}
        missing_keys = sorted(required_keys - set(payload))
        if missing_keys:
            raise ValueError(f"Invalid embedding manifest; missing keys: {', '.join(missing_keys)}")
        persist_path = Path(payload["persist_path"])
        if not persist_path.is_absolute():
            persist_path = settings.paths.project_dir / persist_path
        return cls(
            settings=settings,
            collection_name=payload["collection_name"],
            documents=payload["documents"],
            persist_path=persist_path,
        )

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        query = query.strip()
        if not query:
            return []
        requested_results = self.settings.top_k if top_k is None else top_k
        if requested_results <= 0:
            raise ValueError("top_k must be greater than zero.")
        collection_size = self.collection.count()
        if collection_size == 0:
            return []

        query_embedding = self.embedding_model.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(requested_results, collection_size),
            include=["documents", "metadatas", "distances"],
        )
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        scored: list[SearchResult] = []
        for record_id, content, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
            if not record_id or not metadata or not content:
                continue
            scored.append(
                SearchResult(
                    paper_id=str(metadata.get("paper_id", "")),
                    title=str(metadata.get("title", "")),
                    score=min(1.0, max(0.0, 1.0 - float(distance or 0.0))),
                    content=str(content),
                    metadata=dict(metadata),
                )
            )
        return scored

    def lookup(self, value: str) -> dict[str, Any] | None:
        needle = value.strip().lower()
        if needle in self.documents_by_paper_id:
            return self.documents_by_paper_id[needle]
        if needle in self.documents_by_title:
            return self.documents_by_title[needle]
        return None
