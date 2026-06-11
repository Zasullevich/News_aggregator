from news_app.services.parsing import ParsedItem, SourceType, detect_source_type, normalize_items
from news_app.time import utc_now


def test_detect_source_type():
    assert detect_source_type("https://t.me/s/example") == SourceType.TELEGRAM
    assert detect_source_type("https://example.com/feed.xml") == SourceType.RSS
    assert detect_source_type("https://example.com/news/article") == SourceType.WEBSITE


def test_normalize_items_deduplicates_and_trims_title():
    item = ParsedItem(
        external_id="same",
        title="A" * 600,
        text="Body",
        original_url="https://example.com/a",
        published_at=utc_now(),
    )
    normalized = normalize_items([item, item])
    assert len(normalized) == 1
    assert len(normalized[0].title) == 500
