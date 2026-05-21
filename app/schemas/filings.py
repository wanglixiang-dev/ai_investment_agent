from pydantic import BaseModel, Field


class FilingChunk(BaseModel):
    ticker: str
    chunk_id: int
    score: float
    text: str


class FilingSearchResponse(BaseModel):
    ticker: str
    query: str
    chunks: list[FilingChunk]
    source: str = Field(default="local_filings")
