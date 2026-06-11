import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
from scrapy.http import TextResponse


class SourceType:
    RSS = "rss"
    TELEGRAM = "telegram"
    WEBSITE = "website"

@dataclass(frozen=True)
class ParsedItem:
    external_id: str
    title: str
    text: str
    original_url: str
    published_at: datetime | None = None

def detect_source_type(url: str) -> str:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.lower()
    if host in {"t.me", "telegram.me"} and path.startswith("/s/"):
        return SourceType.TELEGRAM
    if path.endswith((".rss", ".atom", ".xml")) or any(part in path for part in ("/rss", "/feed", "/atom")):
        return SourceType.RSS
    return SourceType.WEBSITE

async def parse_source(source) -> list[ParsedItem]:
    if source.source_type == SourceType.RSS:
        return await parse_rss(source.url)
    if source.source_type == SourceType.TELEGRAM:
        return await parse_telegram(source.url)
    return await parse_website(source.url)

async def parse_rss(url: str) -> list[ParsedItem]:
    content = await _fetch_bytes(url)
    parsed = feedparser.parse(content)
    return [_rss_entry_to_item(entry, url) for entry in parsed.entries]

async def parse_telegram(url: str) -> list[ParsedItem]:
    html = await _fetch_text(url)
    response = _text_response(url, html)
    items = []
    for post in response.css(".tgme_widget_message"):
        text = " ".join(part.strip() for part in post.css(".tgme_widget_message_text ::text").getall() if part.strip())
        permalink = post.css(".tgme_widget_message_date::attr(href)").get()
        published_raw = post.css("time::attr(datetime)").get()
        if not text or not permalink:
            continue
        title = _title_from_text(text)
        items.append(
            ParsedItem(
                external_id=_stable_id(permalink),
                title=title,
                text=text,
                original_url=permalink,
                published_at=_parse_datetime(published_raw),
            )
        )
    return items

async def parse_website(url: str) -> list[ParsedItem]:
    html = await _fetch_text(url)
    response = _text_response(url, html)
    canonical = response.css("link[rel='canonical']::attr(href)").get() or url
    original_url = urljoin(url, canonical)
    title = (
        response.css("meta[property='og:title']::attr(content)").get()
        or response.css("title::text").get()
        or original_url
    )
    text_parts = response.css("article ::text, main ::text, p::text").getall()
    text = " ".join(part.strip() for part in text_parts if part.strip())
    if not text:
        text = title.strip()
    published_raw = (
        response.css("meta[property='article:published_time']::attr(content)").get()
        or response.css("time::attr(datetime)").get()
    )
    return [
        ParsedItem(
            external_id=_stable_id(original_url),
            title=title.strip(),
            text=text,
            original_url=original_url,
            published_at=_parse_datetime(published_raw),
        )
    ]

def normalize_items(items: Iterable[ParsedItem]) -> list[ParsedItem]:
    normalized = []
    seen = set()
    for item in items:
        external_id = item.external_id or _stable_id(item.original_url + item.text[:80])
        if external_id in seen:
            continue
        seen.add(external_id)
        normalized.append(
            ParsedItem(
                external_id=external_id,
                title=(item.title or "Без заголовка").strip()[:500],
                text=(item.text or item.title or "").strip(),
                original_url=item.original_url,
                published_at=item.published_at,
            )
        )
    return normalized

def _rss_entry_to_item(entry, feed_url: str) -> ParsedItem:
    original_url = entry.get("link") or feed_url
    title = entry.get("title") or original_url
    text = entry.get("summary") or entry.get("description") or title
    external_raw = entry.get("id") or entry.get("guid") or original_url or title + text[:80]
    published_raw = entry.get("published") or entry.get("updated")
    return ParsedItem(
        external_id=_stable_id(external_raw),
        title=title,
        text=text,
        original_url=original_url,
        published_at=_parse_datetime(published_raw),
    )

async def _fetch_text(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        response = await client.get(url, headers={"User-Agent": "NewsMvpParser/1.0"})
        response.raise_for_status()
        return response.text

async def _fetch_bytes(url: str) -> bytes:
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        response = await client.get(url, headers={"User-Agent": "NewsMvpParser/1.0"})
        response.raise_for_status()
        return response.content

def _text_response(url: str, html: str) -> TextResponse:
    return TextResponse(url=url, body=html.encode("utf-8"), encoding="utf-8")

def _stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def _title_from_text(text: str) -> str:
    first_line = text.splitlines()[0].strip()
    if len(first_line) > 90:
        return first_line[:87] + "..."
    return first_line or "Пост Telegram"

def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo:
        return parsed.astimezone().replace(tzinfo=None)
    return parsed