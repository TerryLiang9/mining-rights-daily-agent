from mining_agent_shared.config import Settings


def test_settings_include_provider_source_configuration():
    settings = Settings(
        mining_news_rss_feeds="https://example.com/mining.xml, https://example.com/metals.xml",
        mineral_pdf_default_url="https://example.com/report.pdf",
        price_data_file="data/prices/live.json",
        price_data_url="https://example.com/prices.json",
        use_fixtures_on_failure=False,
    )

    assert settings.mining_news_rss_feeds == "https://example.com/mining.xml, https://example.com/metals.xml"
    assert settings.mineral_pdf_default_url == "https://example.com/report.pdf"
    assert settings.price_data_file == "data/prices/live.json"
    assert settings.price_data_url == "https://example.com/prices.json"
    assert settings.use_fixtures_on_failure is False
