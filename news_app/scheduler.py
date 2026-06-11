import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from news_app.services.refresh import refresh_all_sources


logger = logging.getLogger(__name__)
_scheduler = None

def start_scheduler(app):
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")

    def scheduled_refresh():
        with app.app_context():
            try:
                asyncio.run(refresh_all_sources())
            except Exception:
                logger.exception("Scheduled refresh failed")

    _scheduler.add_job(
        scheduled_refresh,
        "interval",
        minutes=app.config["REFRESH_INTERVAL_MINUTES"],
        id="refresh_all_sources",
        max_instances=1,
        replace_existing=True,
    )
    _scheduler.start()
    return _scheduler
