"""Query-side of the RAG layer: text in, ranked catalogue context out."""

from loguru import logger

from arp.llm.provider import LLMProvider
from arp.rag.store import Hit, VectorStore


class Retriever:
    def __init__(self, store: VectorStore, provider: LLMProvider) -> None:
        self._store = store
        self._provider = provider

    def search(self, query: str, k: int = 5) -> list[Hit]:
        (embedding,) = self._provider.embed([query])
        hits = self._store.search(embedding, k)
        logger.debug("retrieval k={} → {} hits for {!r}", k, len(hits), query)
        return hits
