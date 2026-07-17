from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from src.core.config import logger
from src.db.repositories.jobs import JobRepo

ORG_ID = "00000000-0000-0000-0000-000000000001"


def enqueue_daily_briefing():
    logger.info("Scheduler: enqueuing daily briefing job")
    repo = JobRepo()
    repo.enqueue(ORG_ID, "daily_briefing", payload={"auto": True})


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        enqueue_daily_briefing,
        "cron",
        hour=8,
        minute=0,
        timezone="Asia/Kuala_Lumpur",
        id="daily_briefing",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — daily briefing at 08:00 MYT")
    return scheduler
