from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.schemas.filings import FilingAnswerResponse, FilingSearchResponse
from app.tools.filings import FilingRagError, answer_filing_question, search_filing_context


router = APIRouter(prefix="/filings", tags=["filings"])


@router.get("/{ticker}/search", response_model=FilingSearchResponse)
def search_filings(
    ticker: str,
    query: Annotated[str, Query(min_length=1)],
    top_k: Annotated[int, Query(ge=1, le=10)] = 3,
    form: Annotated[str | None, Query(pattern="^(10-K|10-Q)$")] = None,
) -> FilingSearchResponse:
    try:
        return search_filing_context(ticker=ticker, query=query, top_k=top_k, form=form)
    except FilingRagError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{ticker}/answer", response_model=FilingAnswerResponse)
def answer_from_filings(
    ticker: str,
    query: Annotated[str, Query(min_length=1)],
    top_k: Annotated[int, Query(ge=1, le=10)] = 3,
    form: Annotated[str | None, Query(pattern="^(10-K|10-Q)$")] = None,
) -> FilingAnswerResponse:
    try:
        return answer_filing_question(ticker=ticker, query=query, top_k=top_k, form=form)
    except FilingRagError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
