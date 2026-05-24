from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.tools.filings import (
    FilingRagError,
    _html_to_text,
    answer_filing_question,
    search_filing_context,
)


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
        "app.tools.filings.get_settings",
        lambda: SimpleNamespace(
            filing_data_dir=str(filing_dir),
            filing_vector_dir=str(tmp_path / "vectors"),
        ),
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
        "app.tools.filings.get_settings",
        lambda: SimpleNamespace(
            filing_data_dir=str(filing_dir),
            filing_vector_dir=str(tmp_path / "vectors"),
        ),
    )

    response = client.get("/filings/msft/search", params={"query": "cloud margin"})

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "MSFT"
    assert body["chunks"][0]["score"] > 0


def test_search_filings_route_returns_404_for_missing_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "app.tools.filings.get_settings",
        lambda: SimpleNamespace(
            filing_data_dir=str(tmp_path),
            filing_vector_dir=str(tmp_path / "vectors"),
        ),
    )
    monkeypatch.setattr(
        "app.tools.filings._lookup_cik",
        lambda ticker: (_ for _ in ()).throw(FilingRagError("No SEC CIK mapping found for TSLA.")),
    )

    response = client.get("/filings/tsla/search", params={"query": "risk"})

    assert response.status_code == 404
    assert response.json()["detail"] == "No SEC CIK mapping found for TSLA."


def test_search_filing_context_fetches_sec_filing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "app.tools.filings.get_settings",
        lambda: SimpleNamespace(
            filing_data_dir=str(tmp_path / "filings"),
            filing_vector_dir=str(tmp_path / "vectors"),
            sec_archives_base_url="https://www.sec.gov/Archives/edgar/data",
            sec_submissions_base_url="https://data.sec.gov/submissions",
        ),
    )
    monkeypatch.setattr("app.tools.filings._lookup_cik", lambda ticker: "0000320193")
    monkeypatch.setattr(
        "app.tools.filings._fetch_json",
        lambda url: {
            "filings": {
                "recent": {
                    "form": ["8-K", "10-Q"],
                    "accessionNumber": ["ignore", "0000320193-26-000001"],
                    "primaryDocument": ["ignore.htm", "aapl-20260328.htm"],
                    "filingDate": ["2026-01-01", "2026-04-30"],
                    "reportDate": ["2026-01-01", "2026-03-28"],
                }
            }
        },
    )
    monkeypatch.setattr(
        "app.tools.filings._fetch_text",
        lambda url: (
            "<html><body><h1>Item 2. Management Discussion</h1>"
            "Revenue increased because services demand improved. "
            "Gross margin was affected by product mix and supply costs."
            "</body></html>"
        ),
    )

    result = search_filing_context("aapl", "revenue gross margin", form="10-Q")

    assert result.source == "sec_edgar"
    assert result.form == "10-Q"
    assert result.filing_date == "2026-04-30"
    assert result.chunks[0].score > 0
    assert (tmp_path / "vectors").exists()


def test_search_filing_context_filters_xbrl_noise(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "app.tools.filings.get_settings",
        lambda: SimpleNamespace(
            filing_data_dir=str(tmp_path / "filings"),
            filing_vector_dir=str(tmp_path / "vectors"),
            sec_archives_base_url="https://www.sec.gov/Archives/edgar/data",
            sec_submissions_base_url="https://data.sec.gov/submissions",
        ),
    )
    monkeypatch.setattr("app.tools.filings._lookup_cik", lambda ticker: "0001045810")
    monkeypatch.setattr(
        "app.tools.filings._fetch_json",
        lambda url: {
            "filings": {
                "recent": {
                    "form": ["10-Q"],
                    "accessionNumber": ["0001045810-26-000052"],
                    "primaryDocument": ["nvda-20260426.htm"],
                    "filingDate": ["2026-05-27"],
                    "reportDate": ["2026-04-26"],
                }
            }
        },
    )
    monkeypatch.setattr(
        "app.tools.filings._fetch_text",
        lambda url: (
            "<html><body>"
            "<p>nvda:ComputeAndNetworkingMember us-gaap:SalesRevenueNetMember "
            "nvda:CustomerOneMember us-gaap:CustomerConcentrationRiskMember "
            "nvda:A2040NotesMember us-gaap:NotesPayableOtherPayablesMember "
            "2026-01-26 2026-04-26 0001045810 0001045810 0001045810</p>"
            "<h1>Item 2. Management's Discussion and Analysis</h1>"
            "<p>Revenue increased from the prior year because demand for accelerated "
            "computing products remained strong across data center customers. Gross "
            "margin improved as product mix shifted toward higher margin platforms "
            "and operating expenses were managed against expected growth.</p>"
            "</body></html>"
        ),
    )

    result = search_filing_context("nvda", "revenue gross margin", form="10-Q")

    assert result.chunks
    assert "nvda:ComputeAndNetworkingMember" not in result.chunks[0].text
    assert "Revenue increased" in result.chunks[0].text


def test_html_to_text_skips_inline_xbrl_tags() -> None:
    text = _html_to_text(
        "<html><body>"
        "<ix:nonNumeric name=\"dei:EntityRegistrantName\">NOISE CORP</ix:nonNumeric>"
        "<p>The company generated revenue from enterprise demand.</p>"
        "</body></html>"
    )

    assert "NOISE CORP" not in text
    assert "enterprise demand" in text


def test_answer_filing_question_uses_retrieved_context(monkeypatch, tmp_path: Path) -> None:
    filing_dir = tmp_path / "filings"
    filing_dir.mkdir()
    (filing_dir / "AAPL.txt").write_text(
        "Revenue increased because services demand improved. Liquidity remained adequate.",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.tools.filings.get_settings",
        lambda: SimpleNamespace(
            filing_data_dir=str(filing_dir),
            filing_vector_dir=str(tmp_path / "vectors"),
        ),
    )

    result = answer_filing_question("AAPL", "why did revenue increase")

    assert "Revenue increased" in result.answer
