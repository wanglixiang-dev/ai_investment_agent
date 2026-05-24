from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.schemas.filings import FilingSearchResponse
from app.tools.filings import FilingRagError, search_filing_context


router = APIRouter(prefix="/filings", tags=["filings"])


@router.get("/{ticker}/search", response_model=FilingSearchResponse)
def search_filings(
    ticker: str,
    query: Annotated[str, Query(min_length=1)],
    top_k: Annotated[int, Query(ge=1, le=10)] = 3,
) -> FilingSearchResponse:
    try:
        return search_filing_context(ticker=ticker, query=query, top_k=top_k)
    except FilingRagError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
