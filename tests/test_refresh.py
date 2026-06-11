import asyncio

from news_app.extensions import db_session
from news_app.models import NewsItem, Source, User
from news_app.services.parsing import ParsedItem, SourceType
from news_app.services.refresh import refresh_all_sources, save_parsed_items


def test_save_parsed_items_deduplicates(app):
    user = User(email="a@example.com")
    user.set_password("password123")
    source = Source(user=user, url="https://example.com/feed.xml", source_type=SourceType.RSS, title="Feed")
    db_session.add_all([user, source])
    db_session.commit()

    item = ParsedItem(
        external_id="one",
        title="Title",
        text="This item has more than ten words and should be saved in the feed",
        original_url="https://example.com/1",
    )
    assert save_parsed_items(user.id, source.id, [item]) == 1
    assert save_parsed_items(user.id, source.id, [item]) == 0
    db_session.commit()
    assert db_session.query(NewsItem).count() == 1


def test_refresh_all_sources_keeps_going_when_one_source_fails(app, monkeypatch):
    user = User(email="b@example.com")
    user.set_password("password123")
    first = Source(user=user, url="https://example.com/one.xml", source_type=SourceType.RSS, title="One")
    second = Source(user=user, url="https://example.com/two.xml", source_type=SourceType.RSS, title="Two")
    db_session.add_all([user, first, second])
    db_session.commit()

    async def fake_parse_source(source):
        if source.id == first.id:
            raise RuntimeError("broken")
        return [ParsedItem("ok", "Title", "This item has more than ten words and should be saved", "https://example.com/ok")]

    monkeypatch.setattr("news_app.services.refresh.parse_source", fake_parse_source)

    summary = asyncio.run(refresh_all_sources())

    assert summary.total_sources == 2
    assert summary.saved_count == 1
    assert summary.errors == ["broken"]


def test_save_parsed_items_skips_short_news(app):
    user = User(email="c@example.com")
    user.set_password("password123")
    source = Source(user=user, url="https://example.com/feed.xml", source_type=SourceType.RSS, title="Feed")
    db_session.add_all([user, source])
    db_session.commit()

    short_item = ParsedItem(
        external_id="short",
        title="Short",
        text="one two three four five six seven eight nine ten",
        original_url="https://example.com/short",
    )
    long_item = ParsedItem(
        external_id="long",
        title="Long",
        text="one two three four five six seven eight nine ten eleven",
        original_url="https://example.com/long",
    )

    assert save_parsed_items(user.id, source.id, [short_item, long_item]) == 1
    db_session.commit()
