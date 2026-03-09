from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.cli import run_sync_once
from app.config import get_settings


def main() -> None:
    settings = get_settings()
    minute, hour, day, month, day_of_week = settings.schedule_cron.split()
    scheduler = BlockingScheduler(timezone="Asia/Hong_Kong")
    scheduler.add_job(
        run_sync_once,
        trigger=CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
        ),
        id="daily-job-sync",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()


if __name__ == "__main__":
    main()
