from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.repositories import create_research_report_record
from app.db.session import get_db
from app.main import app
from app.schemas.workflow import GraphResearchRequest, GraphResearchResponse, WorkflowStep


def test_get_report_markdown_route() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_db():
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_db

    with TestingSessionLocal() as db:
        create_research_report_record(
            db,
            GraphResearchRequest(ticker="aapl"),
            GraphResearchResponse(
                ticker="AAPL",
                horizon="medium_term",
                risk_level="medium",
                final_report="Thesis\nAAPL is a watchlist candidate.",
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

    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/reports/1/markdown")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "# Investment Research Report: AAPL" in response.text
    assert "AAPL is a watchlist candidate." in response.text
