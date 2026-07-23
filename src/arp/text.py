"""Text folding shared by lexical search and the deterministic test embedder."""

import re
import unicodedata

_WORD = re.compile(r"[a-z0-9]+")


def normalize(text: str) -> str:
    """Fold case and accents so 'CHENE' matches 'chêne' in the French catalogue."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def tokenize(text: str) -> list[str]:
    return _WORD.findall(normalize(text))
