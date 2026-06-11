# News MVP

Flask MVP для персональной сводки новостей. Пользователь добавляет RSS/Atom, обычные сайты или открытые Telegram-каналы вида `https://t.me/s/channel_name`; приложение сохраняет новые материалы в его ленту.

## Запуск

```powershell
python -m pip install -r requirements.txt
python run.py
```

После запуска откройте `http://127.0.0.1:5000`.

## Тесты

```powershell
python -m pytest -q
```

## Что внутри

- Flask routes: регистрация, вход, лента, источники, ручное обновление.
- SQLAlchemy models: `User`, `Source`, `NewsItem`.
- SQLite по умолчанию: `instance/news_mvp.sqlite`.
- Async parsing через `httpx`.
- `feedparser` для RSS/Atom.
- Scrapy `TextResponse`/CSS selectors для Telegram `t.me/s` и HTML-страниц.
- APScheduler обновляет активные источники каждые 15 минут.
