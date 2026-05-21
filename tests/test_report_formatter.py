from datetime import UTC, datetime

from app.db.models import ResearchReportRecord
from app.services.report_formatter import format_report_as_markdown


def test_format_report_as_markdown() -> None:
    record = ResearchReportRecord(
        id=1,
        ticker="AAPL",
        horizon="medium_term",
        risk_level="medium",
        final_report="Thesis\nAAPL is a watchlist candidate.",
        steps=[
            {
                "name": "fetch_market_data",
                "status": "success",
                "message": "Fetched quote.",
            }
        ],
        data_sources=["yfinance:quote", "local_filings"],
        errors=[],
        created_at=datetime(2026, 5, 21, tzinfo=UTC),
    )

    markdown = format_report_as_markdown(record)

    assert markdown.startswith("# Investment Research Report: AAPL")
    assert "- Report ID: 1" in markdown
    assert "## Executive Report" in markdown
    assert "AAPL is a watchlist candidate." in markdown
    assert "- yfinance:quote" in markdown
    assert "`fetch_market_data`: success - Fetched quote." in markdown
