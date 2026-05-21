from datetime import UTC, datetime
from typing import Any

import yfinance as yf

from app.cache.json_cache import get_json_cache
from app.core.config import get_settings
from app.schemas.news import NewsAnalysis, NewsArticle, SentimentLabel


class NewsDataError(RuntimeError):
    pass


POSITIVE_KEYWORDS = {
    "beat",
    "bullish",
    "gain",
    "growth",
    "higher",
    "outperform",
    "profit",
    "record",
    "revenue",
    "strong",
    "surge",
    "upgrade",
}

NEGATIVE_KEYWORDS = {
    "bearish",
    "cut",
    "decline",
    "downgrade",
    "fall",
    "investigation",
    "lawsuit",
    "loss",
    "miss",
    "probe",
    "risk",
    "weak",
    "warning",
}


def get_news_analysis(ticker: str, count: int = 10) -> NewsAnalysis:
    symbol = ticker.strip().upper()
    if not symbol:
        raise NewsDataError("Ticker is required.")

    cache_key = f"news_analysis:{symbol}:{count}"
    cached_analysis = get_json_cache().get(cache_key)
    if cached_analysis is not None:
        return NewsAnalysis.model_validate(cached_analysis)

    try:
        raw_articles = yf.Ticker(symbol).get_news(count=count)
    except Exception as exc:
        raise NewsDataError(f"Failed to fetch news for {symbol}.") from exc

    articles = [_normalize_article(article) for article in raw_articles]
    articles = [article for article in articles if article is not None]

    if not articles:
        raise NewsDataError(f"No news data returned for {symbol}.")

    score = _score_articles(articles)
    sentiment = _label_for_score(score)
    key_headlines = [article.title for article in articles[:5]]

    analysis = NewsAnalysis(
        ticker=symbol,
        sentiment=sentiment,
        score=score,
        article_count=len(articles),
        key_headlines=key_headlines,
        summary=_build_summary(symbol, sentiment, score, articles),
        articles=articles,
    )
    get_json_cache().set(
        cache_key,
        analysis.model_dump(mode="json"),
        ttl_seconds=get_settings().news_cache_ttl_seconds,
    )
    return analysis


def _normalize_article(raw_article: dict[str, Any]) -> NewsArticle | None:
    content = raw_article.get("content") or {}
    title = content.get("title") or raw_article.get("title")
    if not title:
        return None

    provider = content.get("provider") or {}
    publisher = (
        provider.get("displayName")
        if isinstance(provider, dict)
        else raw_article.get("publisher")
    )
    link = _extract_link(content) or raw_article.get("link")
    published_at = _parse_published_at(content.get("pubDate"), raw_article)
    summary = content.get("summary") or raw_article.get("summary")

    return NewsArticle(
        title=str(title),
        publisher=_as_optional_str(publisher),
        link=_as_optional_str(link),
        published_at=published_at,
        summary=_as_optional_str(summary),
    )


def _extract_link(content: dict[str, Any]) -> str | None:
    for key in ("clickThroughUrl", "canonicalUrl"):
        value = content.get(key)
        if isinstance(value, dict) and value.get("url"):
            return str(value["url"])

    return None


def _parse_published_at(value: Any, raw_article: dict[str, Any]) -> datetime | None:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    timestamp = raw_article.get("providerPublishTime")
    if isinstance(timestamp, int | float):
        return datetime.fromtimestamp(timestamp, tz=UTC)

    return None


def _score_articles(articles: list[NewsArticle]) -> float:
    total = 0
    for article in articles:
        text = f"{article.title} {article.summary or ''}".lower()
        positive_hits = sum(1 for word in POSITIVE_KEYWORDS if word in text)
        negative_hits = sum(1 for word in NEGATIVE_KEYWORDS if word in text)
        total += positive_hits - negative_hits

    return max(-1.0, min(1.0, total / len(articles)))


def _label_for_score(score: float) -> SentimentLabel:
    if score > 0.15:
        return SentimentLabel.positive
    if score < -0.15:
        return SentimentLabel.negative
    return SentimentLabel.neutral


def _build_summary(
    symbol: str,
    sentiment: SentimentLabel,
    score: float,
    articles: list[NewsArticle],
) -> str:
    return (
        f"{symbol} recent news sentiment is {sentiment.value} "
        f"based on {len(articles)} Yahoo Finance headlines "
        f"with a keyword score of {score:+.2f}."
    )


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None
