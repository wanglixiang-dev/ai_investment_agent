from fastapi import APIRouter, HTTPException

from app.schemas.news import NewsAnalysis
from app.tools.news import NewsDataError, get_news_analysis


router = APIRouter(prefix="/news", tags=["news"])


@router.get("/{ticker}/analysis", response_model=NewsAnalysis)
def read_news_analysis(ticker: str) -> NewsAnalysis:
    try:
        return get_news_analysis(ticker)
    except NewsDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
