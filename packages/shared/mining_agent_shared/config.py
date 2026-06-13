from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_api_host: str = "0.0.0.0"
    agent_api_port: int = 8000
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma"
    use_fixtures_on_failure: bool = True
    mining_news_rss_feeds: str = ""
    mineral_pdf_default_url: str = ""
    price_data_file: str = ""
    price_data_url: str = ""


def get_settings() -> Settings:
    return Settings()
