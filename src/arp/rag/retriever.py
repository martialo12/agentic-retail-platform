"""Query-side of the RAG layer: text in, ranked catalogue context out."""

from arp.llm.provider import LLMProvider
from arp.rag.store import Hit, VectorStore


class Retriever:
    def __init__(self, store: VectorStore, provider: LLMProvider) -> None:
        self._store = store
        self._provider = provider

    def search(self, query: str, k: int = 5) -> list[Hit]:
        (embedding,) = self._provider.embed([query])
        return self._store.search(embedding, k)
