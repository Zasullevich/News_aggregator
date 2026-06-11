import asyncio
from dataclasses import dataclass, field
from sqlalchemy.exc import IntegrityError

from news_app.extensions import db_session
from news_app.models import NewsItem, Source
from news_app.services.parsing import normalize_items, parse_source
from news_app.time import utc_now


@dataclass(frozen=True)
class RefreshResult:
    source_id: int
    saved_count: int = 0
    error: str | None = None


@dataclass(frozen=True)
class RefreshSummary:
    total_sources: int
    saved_count: int
    errors: list[str] = field(default_factory=list)


async def refresh_source(source_id: int) -> RefreshResult:
    source = db_session.get(Source, source_id)
    if not source:
        return RefreshResult(source_id=source_id, error="Источник не найден")
    if not source.enabled:
        return RefreshResult(source_id=source_id, saved_count=0)

    try:
        parsed_items = normalize_items(await parse_source(source))
        saved_count = save_parsed_items(source.user_id, source.id, parsed_items)
        source.last_checked_at = utc_now()
        db_session.commit()
        return RefreshResult(source_id=source.id, saved_count=saved_count)
    except Exception as exc:
        db_session.rollback()
        return RefreshResult(source_id=source.id, error=str(exc))


async def refresh_all_sources() -> RefreshSummary:
    sources = db_session.query(Source).filter(Source.enabled.is_(True)).all()
    results = await asyncio.gather(*(refresh_source(source.id) for source in sources))
    return RefreshSummary(
        total_sources=len(results),
        saved_count=sum(result.saved_count for result in results),
        errors=[result.error for result in results if result.error],
    )


def save_parsed_items(user_id: int, source_id: int, items) -> int:
    saved_count = 0
    for item in items:
        if not item.text or _word_count(item.text) <= 10 or "#реклама" in item.text.lower():
            continue
        exists = (
            db_session.query(NewsItem.id)
            .filter(
                NewsItem.user_id == user_id,
                NewsItem.source_id == source_id,
                NewsItem.external_id == item.external_id,
            )
            .first()
        )
        if exists:
            continue
        news_item = NewsItem(
            user_id=user_id,
            source_id=source_id,
            external_id=item.external_id,
            title=item.title,
            text=item.text,
            original_url=item.original_url,
            published_at=item.published_at,
        )
        db_session.add(news_item)
        try:
            db_session.flush()
            saved_count += 1
        except IntegrityError:
            db_session.rollback()
    return saved_count


def _word_count(text: str) -> int:
    return len([word for word in text.split() if word.strip()])
