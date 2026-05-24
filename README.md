# Multi-Agent Investment Research System

An AI infrastructure project that generates investment research reports by combining a FastAPI backend, LangGraph workflow orchestration, DeepSeek tool calling, market data tools, news analysis, dynamic SEC EDGAR filing RAG, SQL persistence, Redis caching, Docker Compose, GitHub Actions, and a lightweight web UI.

## Features

- FastAPI backend with OpenAPI docs and health checks
- LangGraph research workflow with explicit execution steps
- DeepSeek API tool-calling service using the OpenAI-compatible SDK interface
- yfinance stock quote tool
- yfinance news analysis tool with baseline sentiment scoring
- Dynamic SEC EDGAR filing RAG for latest 10-K/10-Q retrieval, chunking, local vector indexing, and question answering
- SQLAlchemy persistence for saved reports
- Redis-backed JSON cache for quotes and news analysis
- Docker Compose stack with API, PostgreSQL, and Redis
- GitHub Actions CI for automated tests
- Browser UI for generating and viewing reports
- Markdown export for saved reports

## Architecture

```text
Web UI / API Client
        |
        v
FastAPI Routes
        |
        +--> Stock Tool -----------------> yfinance quote data
        +--> News Tool ------------------> yfinance news data
        +--> Filing RAG Tool ------------> SEC EDGAR latest 10-K/10-Q + local vector index
        +--> DeepSeek Tool-Calling Agent --> stock/news tools
        |
        v
LangGraph Workflow
        |
        +--> fetch_market_data
        +--> analyze_news
        +--> retrieve_filing_context
        +--> generate_report
        |
        v
SQLAlchemy Repository ---> SQLite locally / PostgreSQL in Docker
        |
        v
Markdown Export
```

## Tech Stack

- Python 3.13+
- FastAPI
- LangGraph
- DeepSeek API through the OpenAI-compatible Python SDK
- SQLAlchemy 2.x
- PostgreSQL / SQLite
- Redis
- yfinance
- Docker Compose
- GitHub Actions
- Pytest

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Local defaults:

```bash
DATABASE_URL=sqlite:///./investment_agent.db
REDIS_URL=redis://localhost:6379/0
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
FILING_DATA_DIR=data/filings
FILING_VECTOR_DIR=data/filing_vectors
SEC_USER_AGENT=ai-investment-agent contact@example.com
```

PostgreSQL example:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/investment_agent
```

## Docker Compose

```bash
docker compose up --build
```

The Compose stack runs:

- FastAPI API on `8000`
- PostgreSQL on `5432`
- Redis on `6379`

Check service health:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/dependencies
```

## Main APIs

Generate a deterministic LangGraph research report:

```bash
curl -X POST http://127.0.0.1:8000/graph/research \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","horizon":"medium_term","risk_level":"medium"}'
```

Run the DeepSeek tool-calling agent:

```bash
export DEEPSEEK_API_KEY="your_api_key"
export DEEPSEEK_MODEL="deepseek-v4-flash"

curl -X POST http://127.0.0.1:8000/agent/research \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","horizon":"medium_term","risk_level":"medium"}'
```

Fetch stock quote:

```bash
curl http://127.0.0.1:8000/stocks/AAPL/quote
```

Analyze news:

```bash
curl http://127.0.0.1:8000/news/AAPL/analysis
```

Search SEC filing context. If the latest filing is not already indexed locally, the API maps ticker to CIK, fetches the latest 10-K or 10-Q from SEC EDGAR, chunks it, writes a local vector index under `data/filing_vectors`, then searches it:

```bash
curl "http://127.0.0.1:8000/filings/AAPL/search?query=revenue%20margin%20risk"
```

Answer from retrieved SEC filing context:

```bash
curl "http://127.0.0.1:8000/filings/AAPL/answer?query=what%20does%20management%20say%20about%20margins&form=10-Q"
```

List saved reports:

```bash
curl http://127.0.0.1:8000/reports
```

Export saved report as Markdown:

```bash
curl http://127.0.0.1:8000/reports/1/markdown
```

## Testing

```bash
python -m pytest
```

The test suite mocks external providers where appropriate, so CI does not require DeepSeek credentials, live Redis, PostgreSQL, or Yahoo Finance network access.

## CI

GitHub Actions runs on pushes and pull requests to `main`:

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

Workflow file:

```text
.github/workflows/ci.yml
```

## Project Structure

```text
app/
  api/routes/          FastAPI route handlers
  cache/               Redis JSON cache helpers
  core/                Settings and configuration
  db/                  SQLAlchemy models, sessions, repository helpers
  schemas/             Pydantic request/response models
  services/            Agent workflow and report formatting services
  tools/               Stock, news, and filing RAG tools
  web/                 Static browser UI
data/filings/          Local filing text corpus
tests/                 Pytest suite
```

## Current Limitations

- `yfinance` data can be delayed, incomplete, or rate-limited.
- News sentiment currently uses a transparent keyword baseline.
- Filing RAG uses a lightweight local TF-IDF vector index. It is suitable for the MVP loop, but production-grade semantic retrieval should replace it with embeddings and a dedicated vector database.
- Database migrations are not yet managed by Alembic.
- Redis is used for caching, not yet for background task queues.

## Roadmap

- Add embeddings and pgvector for SEC filing RAG
- Add Alembic migrations
- Add background report generation with a queue
- Add authenticated users and report ownership
- Add richer frontend report views and download support
- Add production deployment configuration
