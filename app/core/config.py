from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Multi-Agent Investment Research System"
    environment: str = "local"
    api_version: str = "0.1.0"
    database_url: str = "sqlite:///./investment_agent.db"
    filing_data_dir: str = "data/filings"
    filing_vector_dir: str = "data/filing_vectors"
    sec_user_agent: str = "ai-investment-agent contact@example.com"
    sec_company_tickers_url: str = "https://www.sec.gov/files/company_tickers_exchange.json"
    sec_submissions_base_url: str = "https://data.sec.gov/submissions"
    sec_archives_base_url: str = "https://www.sec.gov/Archives/edgar/data"
    redis_url: str = "redis://localhost:6379/0"
    stock_quote_cache_ttl_seconds: int = 60
    news_cache_ttl_seconds: int = 900
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
