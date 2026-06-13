from mining_agent_shared.models import (
    Citation,
    EvidencePack,
    NewsItem,
    PricePoint,
    ResourceItem,
    Topic,
)


def test_evidence_pack_tracks_fallback():
    pack = EvidencePack(
        topic=Topic(raw_query="Pilbara lithium", region="Pilbara", commodity="lithium"),
        news=[
            NewsItem(
                title="Pilbara lithium update",
                url="https://example.com/news",
                source="fixture",
                published_at="2026-06-13",
                summary="Sample update",
                score=0.9,
            )
        ],
        resources=[
            ResourceItem(
                category="Indicated",
                ore_tonnage=120.5,
                ore_tonnage_unit="Mt",
                grade=1.25,
                grade_unit="% Li2O",
                contained_metal=1.5,
                contained_metal_unit="Mt LCE",
                page=42,
                confidence=0.8,
            )
        ],
        prices=[PricePoint(date="2026-06-13", price=12850.0)],
        citations=[Citation(label="fixture news", url="https://example.com/news", source_type="news")],
        fallback_used=True,
        warnings=["Using fixture data"],
    )

    assert pack.fallback_used is True
    assert pack.topic.commodity == "lithium"
    assert pack.citations[0].source_type == "news"
