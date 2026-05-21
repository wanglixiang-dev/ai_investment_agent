from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.repositories import (
    create_research_report_record,
    get_research_report_record,
    list_research_report_records,
)
from app.schemas.workflow import GraphResearchRequest, GraphResearchResponse, WorkflowStep


def test_create_and_read_research_report_record() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        record = create_research_report_record(
            db,
            GraphResearchRequest(ticker="aapl"),
            GraphResearchResponse(
                ticker="AAPL",
                horizon="medium_term",
                risk_level="medium",
                final_report="Final report",
                steps=[
                    WorkflowStep(
                        name="generate_report",
                        status="success",
                        message="Generated report.",
                    )
                ],
                data_sources=["yfinance:quote"],
                errors=[],
            ),
        )

        loaded = get_research_report_record(db, record.id)
        records = list_research_report_records(db)

    assert loaded is not None
    assert loaded.ticker == "AAPL"
    assert loaded.final_report == "Final report"
    assert loaded.steps[0]["name"] == "generate_report"
    assert len(records) == 1
