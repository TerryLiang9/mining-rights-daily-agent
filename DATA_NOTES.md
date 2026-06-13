# Data Notes

The project uses fixture data when external mining news, PDF, or price sources are unavailable. Fallback use is explicit in the API response, CLI output, Web Dashboard, and generated report.

## Core Schemas

- News item: title, url, source, published_at, summary, score.
- Resource item: category, ore tonnage, grade, contained metal, units, page, confidence.
- Price point: commodity, date, price, currency, unit.
- Evidence pack: topic, news, resources, prices, citations, tool trace, data_quality.

## Data Quality Rules

- Missing PDF evidence returns abstain or fixture data.
- Unsupported commodity returns a structured warning.
- Generated reports must disclose fallback data.
