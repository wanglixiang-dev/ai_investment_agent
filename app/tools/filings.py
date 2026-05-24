import gzip
import html
import json
import math
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.schemas.filings import FilingAnswerResponse, FilingChunk, FilingSearchResponse


class FilingRagError(RuntimeError):
    pass


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "the",
    "to",
    "we",
    "with",
}

FILING_FORMS = {"10-K", "10-Q"}
SECTION_RE = re.compile(
    r"\b((?:part\s+[ivx]+\.?\s+)?item\s+\d+[a-z]?\.?)\s+([^.\n]{0,90})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FilingDocument:
    ticker: str
    cik: str
    form: str
    accession_number: str
    filing_date: str
    report_date: str | None
    primary_document: str
    source_url: str
    text: str


def search_filing_context(
    ticker: str,
    query: str,
    top_k: int = 3,
    form: str | None = None,
) -> FilingSearchResponse:
    symbol = _normalize_ticker(ticker)
    chunks = _ensure_indexed(symbol, form=form)
    ranked_chunks = _rank_chunks(chunks, query)
    relevant_chunks = ranked_chunks[:top_k]
    if not relevant_chunks:
        raise FilingRagError(f"No filing chunks are available for {symbol}.")

    first = relevant_chunks[0]
    return FilingSearchResponse(
        ticker=symbol,
        query=query,
        chunks=relevant_chunks,
        source="local_filings"
        if (first.accession_number or "").startswith("local-")
        else "sec_edgar",
        form=first.form,
        filing_date=first.filing_date,
        accession_number=first.accession_number,
        source_url=first.source_url,
    )


def answer_filing_question(
    ticker: str,
    query: str,
    top_k: int = 3,
    form: str | None = None,
) -> FilingAnswerResponse:
    result = search_filing_context(ticker=ticker, query=query, top_k=top_k, form=form)
    answer = _build_extractive_answer(result)
    return FilingAnswerResponse(**result.model_dump(), answer=answer)


def _ensure_indexed(symbol: str, form: str | None = None) -> list[FilingChunk]:
    existing_chunks = _load_latest_index(symbol, form=form)
    if existing_chunks:
        return existing_chunks

    filing_path = _filing_path(symbol)
    if filing_path.exists():
        document = filing_path.read_text(encoding="utf-8")
        if not document.strip():
            raise FilingRagError(f"Local filing document for {symbol} is empty.")
        return _index_document(
            FilingDocument(
                ticker=symbol,
                cik="",
                form=form or "LOCAL",
                accession_number=f"local-{symbol}",
                filing_date="",
                report_date=None,
                primary_document=filing_path.name,
                source_url=str(filing_path),
                text=document,
            )
        )

    document = _fetch_latest_sec_filing(symbol, form=form)
    return _index_document(document)


def _fetch_latest_sec_filing(symbol: str, form: str | None = None) -> FilingDocument:
    cik = _lookup_cik(symbol)
    settings = get_settings()
    submissions_base_url = getattr(
        settings,
        "sec_submissions_base_url",
        "https://data.sec.gov/submissions",
    )
    archives_base_url = getattr(
        settings,
        "sec_archives_base_url",
        "https://www.sec.gov/Archives/edgar/data",
    )
    submission = _fetch_json(f"{submissions_base_url}/CIK{cik}.json")
    recent = submission.get("filings", {}).get("recent", {})
    filing = _select_latest_filing(recent, form=form)
    cik_for_archive = str(int(cik))
    accession_path = filing["accession_number"].replace("-", "")
    source_url = (
        f"{archives_base_url}/{cik_for_archive}/"
        f"{accession_path}/{filing['primary_document']}"
    )
    raw_document = _fetch_text(source_url)
    text = _html_to_text(raw_document)
    if not text.strip():
        raise FilingRagError(f"SEC filing document for {symbol} was empty after parsing.")

    return FilingDocument(
        ticker=symbol,
        cik=cik,
        form=filing["form"],
        accession_number=filing["accession_number"],
        filing_date=filing["filing_date"],
        report_date=filing["report_date"],
        primary_document=filing["primary_document"],
        source_url=source_url,
        text=text,
    )


def _lookup_cik(symbol: str) -> str:
    settings = get_settings()
    company_tickers_url = getattr(
        settings,
        "sec_company_tickers_url",
        "https://www.sec.gov/files/company_tickers_exchange.json",
    )
    data = _fetch_json(company_tickers_url)
    fields = data.get("fields")
    rows = data.get("data")
    if isinstance(fields, list) and isinstance(rows, list):
        for row in rows:
            item = dict(zip(fields, row, strict=False))
            if str(item.get("ticker", "")).upper() == symbol:
                return str(item["cik"]).zfill(10)

    for value in data.values():
        if isinstance(value, dict) and str(value.get("ticker", "")).upper() == symbol:
            return str(value["cik_str"]).zfill(10)

    raise FilingRagError(f"No SEC CIK mapping found for {symbol}.")


def _select_latest_filing(recent: dict[str, list[Any]], form: str | None = None) -> dict[str, str | None]:
    requested_forms = {_normalize_form(form)} if form else FILING_FORMS
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    primary_documents = recent.get("primaryDocument", [])
    filing_dates = recent.get("filingDate", [])
    report_dates = recent.get("reportDate", [])

    for index, filing_form in enumerate(forms):
        if filing_form not in requested_forms:
            continue
        if index >= len(accessions) or index >= len(primary_documents):
            continue
        return {
            "form": filing_form,
            "accession_number": str(accessions[index]),
            "primary_document": str(primary_documents[index]),
            "filing_date": str(filing_dates[index]) if index < len(filing_dates) else "",
            "report_date": str(report_dates[index]) if index < len(report_dates) else None,
        }

    forms_label = ", ".join(sorted(requested_forms))
    raise FilingRagError(f"No recent {forms_label} filing found in SEC submissions.")


def _index_document(document: FilingDocument) -> list[FilingChunk]:
    chunk_texts = _chunk_text(document.text)
    if not chunk_texts:
        raise FilingRagError(f"Filing document for {document.ticker} is empty.")

    chunks = [
        FilingChunk(
            ticker=document.ticker,
            chunk_id=index,
            score=0.0,
            text=chunk,
            form=document.form,
            filing_date=document.filing_date,
            accession_number=document.accession_number,
            section=_detect_section(chunk),
            source_url=document.source_url,
        )
        for index, chunk in enumerate(chunk_texts)
    ]
    _save_index(document.ticker, document.accession_number, chunks)
    return chunks


def _load_latest_index(symbol: str, form: str | None = None) -> list[FilingChunk]:
    vector_dir = _vector_dir()
    if not vector_dir.exists():
        return []

    requested_form = _normalize_form(form) if form else None
    candidates = sorted(vector_dir.glob(f"{symbol}_*.json"), reverse=True)
    for candidate in candidates:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        chunks = [FilingChunk.model_validate(item) for item in payload.get("chunks", [])]
        if not chunks:
            continue
        if requested_form is None or chunks[0].form == requested_form:
            return chunks
    return []


def _save_index(symbol: str, accession_number: str, chunks: list[FilingChunk]) -> None:
    vector_dir = _vector_dir()
    vector_dir.mkdir(parents=True, exist_ok=True)
    safe_accession = re.sub(r"[^A-Za-z0-9_-]", "-", accession_number)
    path = vector_dir / f"{symbol}_{safe_accession}.json"
    payload = {"chunks": [chunk.model_dump(mode="json") for chunk in chunks]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _rank_chunks(chunks: list[FilingChunk], query: str) -> list[FilingChunk]:
    query_terms = _tokenize(query)
    if not query_terms:
        return chunks

    document_frequency: dict[str, int] = {}
    chunk_terms = []
    for chunk in chunks:
        terms = _tokenize(chunk.text)
        chunk_terms.append(terms)
        for term in set(terms):
            document_frequency[term] = document_frequency.get(term, 0) + 1

    query_vector = _tfidf_vector(query_terms, document_frequency, len(chunks))
    ranked = []
    for chunk, terms in zip(chunks, chunk_terms, strict=True):
        chunk_vector = _tfidf_vector(terms, document_frequency, len(chunks))
        ranked.append(chunk.model_copy(update={"score": _cosine_similarity(query_vector, chunk_vector)}))

    return sorted(ranked, key=lambda chunk: chunk.score, reverse=True)


def _tfidf_vector(terms: list[str], document_frequency: dict[str, int], document_count: int) -> dict[str, float]:
    vector: dict[str, float] = {}
    if not terms:
        return vector

    for term in terms:
        tf = terms.count(term) / len(terms)
        idf = math.log((document_count + 1) / (document_frequency.get(term, 0) + 1)) + 1
        vector[term] = tf * idf
    return vector


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0

    dot = sum(left_term_weight * right.get(term, 0.0) for term, left_term_weight in left.items())
    left_norm = math.sqrt(sum(weight * weight for weight in left.values()))
    right_norm = math.sqrt(sum(weight * weight for weight in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _build_extractive_answer(result: FilingSearchResponse) -> str:
    snippets = []
    for chunk in result.chunks:
        sentence = _best_sentence(chunk.text, result.query)
        if sentence:
            snippets.append(sentence)

    evidence = " ".join(snippets[:3]).strip()
    if not evidence:
        evidence = result.chunks[0].text[:500].strip()

    citation = result.form or "filing"
    if result.filing_date:
        citation = f"{citation} filed {result.filing_date}"
    return f"Based on the retrieved {citation} context: {evidence}"


def _best_sentence(text: str, query: str) -> str:
    query_terms = set(_tokenize(query))
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if not sentences:
        return text[:300]

    return max(
        sentences,
        key=lambda sentence: len(query_terms.intersection(_tokenize(sentence))),
    ).strip()


def _chunk_text(document: str, max_words: int = 220, overlap_words: int = 40) -> list[str]:
    words = document.split()
    if not words:
        return []

    chunks = []
    step = max_words - overlap_words
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + max_words]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def _detect_section(text: str) -> str | None:
    match = SECTION_RE.search(text)
    if not match:
        return None
    title = " ".join(part.strip(" .") for part in match.groups() if part.strip())
    return re.sub(r"\s+", " ", title)


def _fetch_json(url: str) -> dict[str, Any]:
    try:
        with urlopen(_request(url), timeout=20) as response:
            return json.loads(_read_response_text(response))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise FilingRagError(f"Failed to fetch SEC JSON data from {url}.") from exc


def _fetch_text(url: str) -> str:
    try:
        with urlopen(_request(url), timeout=30) as response:
            return _read_response_text(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise FilingRagError(f"Failed to fetch SEC filing document from {url}.") from exc


def _request(url: str) -> Request:
    user_agent = getattr(
        get_settings(),
        "sec_user_agent",
        "ai-investment-agent contact@example.com",
    )
    return Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip",
        },
    )


def _read_response_text(response: Any) -> str:
    body = response.read()
    if response.headers.get("Content-Encoding") == "gzip":
        body = gzip.decompress(body)
    return body.decode("utf-8", errors="replace")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1
        if tag in {"br", "div", "p", "tr", "li", "h1", "h2", "h3"}:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in {"div", "p", "tr", "li", "h1", "h2", "h3"}:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self.parts.append(data)


def _html_to_text(raw_document: str) -> str:
    parser = _TextExtractor()
    parser.feed(raw_document)
    text = html.unescape(" ".join(parser.parts))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _filing_path(ticker: str) -> Path:
    settings = get_settings()
    return Path(settings.filing_data_dir) / f"{ticker}.txt"


def _vector_dir() -> Path:
    settings = get_settings()
    return Path(getattr(settings, "filing_vector_dir", "data/filing_vectors"))


def _normalize_ticker(ticker: str) -> str:
    symbol = ticker.strip().upper()
    if not symbol:
        raise FilingRagError("Ticker is required.")
    return symbol


def _normalize_form(form: str | None) -> str:
    normalized = (form or "").strip().upper()
    if normalized not in FILING_FORMS:
        raise FilingRagError("Form must be either 10-K or 10-Q.")
    return normalized


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9]+", text.lower())
    return [token for token in tokens if token not in STOPWORDS]
