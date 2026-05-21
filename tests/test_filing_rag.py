from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.tools.filing_rag import search_filing_context


client = TestClient(app)


def test_search_filing_context(monkeypatch, tmp_path: Path) -> None:
    filing_dir = tmp_path / "filings"
    filing_dir.mkdir()
    (filing_dir / "AAPL.txt").write_text(
        "Revenue growth depends on iPhone demand and services margin. "
        "Supply chain disruption can pressure gross margin and product availability.",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.tools.filing_rag.get_settings",
        lambda: SimpleNamespace(filing_data_dir=str(filing_dir)),
    )

    result = search_filing_context("aapl", "revenue margin supply chain")

    assert result.ticker == "AAPL"
    assert result.source == "local_filings"
    assert len(result.chunks) == 1
    assert result.chunks[0].score > 0


def test_search_filings_route(monkeypatch, tmp_path: Path) -> None:
    filing_dir = tmp_path / "filings"
    filing_dir.mkdir()
    (filing_dir / "MSFT.txt").write_text(
        "Cloud revenue and operating margin depend on enterprise demand.",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.tools.filing_rag.get_settings",
        lambda: SimpleNamespace(filing_data_dir=str(filing_dir)),
    )

    response = client.get("/filings/msft/search", params={"query": "cloud margin"})

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "MSFT"
    assert body["chunks"][0]["score"] > 0


def test_search_filings_route_returns_404_for_missing_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "app.tools.filing_rag.get_settings",
        lambda: SimpleNamespace(filing_data_dir=str(tmp_path)),
    )

    response = client.get("/filings/tsla/search", params={"query": "risk"})

    assert response.status_code == 404
    assert response.json()["detail"] == "No local filing document found for TSLA."
