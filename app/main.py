from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.agent import router as agent_router
from app.api.routes.filings import router as filings_router
from app.api.routes.graph import router as graph_router
from app.api.routes.health import router as health_router
from app.api.routes.news import router as news_router
from app.api.routes.research import router as research_router
from app.api.routes.reports import router as reports_router
from app.api.routes.stocks import router as stocks_router
from app.core.config import get_settings
from app.db.session import create_db_and_tables


settings = get_settings()
WEB_DIR = Path(__file__).parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    create_db_and_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    lifespan=lifespan,
)

app.include_router(agent_router)
app.include_router(filings_router)
app.include_router(graph_router)
app.include_router(health_router)
app.include_router(news_router)
app.include_router(research_router)
app.include_router(reports_router)
app.include_router(stocks_router)
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


@app.get("/")
def read_root() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")
