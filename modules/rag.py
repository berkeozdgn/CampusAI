from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

from config import CHROMA_PATH, EMBEDDING_MODEL
from modules.pdf_utils import read_pdf, split_text


class RagService:
    def __init__(self) -> None:
        self._embedding_model = None
        self._chroma_client = None

    @property
    def embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(
                EMBEDDING_MODEL
            )

        return self._embedding_model

    @property
    def chroma_client(self):
        if self._chroma_client is None:
            CHROMA_PATH.mkdir(
                parents=True,
                exist_ok=True,
            )

            self._chroma_client = (
                chromadb.PersistentClient(
                    path=str(CHROMA_PATH)
                )
            )

        return self._chroma_client

    def index_pdfs(
        self,
        uploaded_files: list[Any],
    ) -> dict[str, Any]:
        from modules.pdf_utils import (
            create_collection_name,
        )

        collection_name = (
            create_collection_name(
                uploaded_files
            )
        )

        try:
            self.chroma_client.delete_collection(
                collection_name
            )
        except Exception:
            pass

        collection = (
            self.chroma_client
            .create_collection(
                name=collection_name
            )
        )

        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        ids: list[str] = []
        file_summaries: list[
            dict[str, Any]
        ] = []

        chunk_counter = 0

        for uploaded_file in uploaded_files:
            pages = read_pdf(uploaded_file)
            file_chunk_count = 0

            for page in pages:
                chunks = split_text(
                    page["text"]
                )

                for chunk in chunks:
                    documents.append(chunk)

                    metadatas.append(
                        {
                            "page": page["page"],
                            "file_name": (
                                uploaded_file.name
                            ),
                        }
                    )

                    ids.append(
                        f"chunk_{chunk_counter}"
                    )

                    chunk_counter += 1
                    file_chunk_count += 1

            file_summaries.append(
                {
                    "file_name": (
                        uploaded_file.name
                    ),
                    "page_count": len(pages),
                    "chunk_count": (
                        file_chunk_count
                    ),
                }
            )

        if not documents:
            raise ValueError(
                "PDF dosyalarında okunabilir "
                "metin bulunamadı. Dosyalar "
                "taranmış görüntülerden "
                "oluşuyor olabilir."
            )

        embeddings = (
            self.embedding_model.encode(
                documents,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            .tolist()
        )

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        return {
            "collection_name": (
                collection_name
            ),
            "files": file_summaries,
            "total_file_count": (
                len(uploaded_files)
            ),
            "total_chunk_count": (
                len(documents)
            ),
        }

    def search(
        self,
        question: str,
        collection_name: str,
        result_count: int = 5,
    ) -> list[dict[str, Any]]:
        collection = (
            self.chroma_client
            .get_collection(
                collection_name
            )
        )

        question_embedding = (
            self.embedding_model.encode(
                question,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            .tolist()
        )

        results = collection.query(
            query_embeddings=[
                question_embedding
            ],
            n_results=result_count,
        )

        documents = results.get(
            "documents",
            [[]],
        )[0]

        metadatas = results.get(
            "metadatas",
            [[]],
        )[0]

        sources: list[
            dict[str, Any]
        ] = []

        for document, metadata in zip(
            documents,
            metadatas,
        ):
            sources.append(
                {
                    "text": document,
                    "page": metadata.get(
                        "page",
                        "?",
                    ),
                    "file_name": (
                        metadata.get(
                            "file_name",
                            "Bilinmeyen PDF",
                        )
                    ),
                }
            )

        return sources

    def delete_collection(
        self,
        collection_name: str,
    ) -> None:
        try:
            self.chroma_client.delete_collection(
                collection_name
            )
        except Exception:
            pass