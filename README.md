# News Aggregator

Сайт агрегатор сбора новостей с указанных пользователем ссылок. Пользователь добавляет RSS/Atom, обычные сайты или открытые Telegram-каналы вида https://t.me/s/channel_name и сохраняет в своей ленте.

## Запуск

python -m pip install -r requirements.txt
python run.py

После запуска откройте http://127.0.0.1:5000.

## Тесты

python -m pytest -q

## Набор инструментов

- Flask
- SQLAlchemy
- SQLite
- Async через httpx.
- feedparser для RSS/Atom.
- Scrapy
- APScheduler обновляет активные источники каждые 15 минут.
