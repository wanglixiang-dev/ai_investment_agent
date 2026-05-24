from pydantic import BaseModel, Field


class FilingChunk(BaseModel):
    ticker: str
    chunk_id: int
    score: float
    text: str
    form: str | None = None
    filing_date: str | None = None
    accession_number: str | None = None
    section: str | None = None
    source_url: str | None = None


class FilingSearchResponse(BaseModel):
    ticker: str
    query: str
    chunks: list[FilingChunk]
    source: str = Field(default="sec_edgar")
    form: str | None = None
    filing_date: str | None = None
    accession_number: str | None = None
    source_url: str | None = None


class FilingAnswerResponse(FilingSearchResponse):
    answer: str
