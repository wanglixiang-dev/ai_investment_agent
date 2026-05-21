import re
from pathlib import Path

from app.core.config import get_settings
from app.schemas.filings import FilingChunk, FilingSearchResponse


class FilingRagError(RuntimeError):
    pass


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def search_filing_context(
    ticker: str,
    query: str,
    top_k: int = 3,
) -> FilingSearchResponse:
    symbol = ticker.strip().upper()
    if not symbol:
        raise FilingRagError("Ticker is required.")

    filing_path = _filing_path(symbol)
    if not filing_path.exists():
        raise FilingRagError(f"No local filing document found for {symbol}.")

    document = filing_path.read_text(encoding="utf-8")
    chunks = _chunk_text(document)
    if not chunks:
        raise FilingRagError(f"Local filing document for {symbol} is empty.")

    query_terms = _tokenize(query)
    ranked_chunks = sorted(
        (
            FilingChunk(
                ticker=symbol,
                chunk_id=index,
                score=_score_chunk(chunk, query_terms),
                text=chunk,
            )
            for index, chunk in enumerate(chunks)
        ),
        key=lambda chunk: chunk.score,
        reverse=True,
    )

    relevant_chunks = [chunk for chunk in ranked_chunks if chunk.score > 0][:top_k]
    if not relevant_chunks:
        relevant_chunks = ranked_chunks[:top_k]

    return FilingSearchResponse(
        ticker=symbol,
        query=query,
        chunks=relevant_chunks,
    )


def _filing_path(ticker: str) -> Path:
    settings = get_settings()
    return Path(settings.filing_data_dir) / f"{ticker}.txt"


def _chunk_text(document: str, max_words: int = 120) -> list[str]:
    words = document.split()
    chunks = []
    for start in range(0, len(words), max_words):
        chunk = " ".join(words[start : start + max_words]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def _score_chunk(chunk: str, query_terms: set[str]) -> float:
    if not query_terms:
        return 0.0

    chunk_terms = _tokenize(chunk)
    if not chunk_terms:
        return 0.0

    overlap = query_terms.intersection(chunk_terms)
    return len(overlap) / len(query_terms)


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9]+", text.lower())
    return {token for token in tokens if token not in STOPWORDS}
