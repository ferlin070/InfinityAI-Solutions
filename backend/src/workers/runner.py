import time
import os
from src.core.config import logger
from src.db.repositories.jobs import JobRepo
from src.workers.handlers import process_inbound, generate_quotation, daily_briefing

HANDLERS = {
    "process_inbound": process_inbound,
    "generate_quotation": generate_quotation,
    "daily_briefing": daily_briefing,
}


def run_worker():
    logger.info("Worker started — polling for jobs...")
    repo = JobRepo()
    while True:
        try:
            job = repo.claim_next()
            if job is None:
                time.sleep(2)
                continue

            handler = HANDLERS.get(job["type"])
            if handler is None:
                logger.warning(f"No handler for job type: {job['type']}")
                repo.fail(job["id"], f"Unknown job type: {job['type']}")
                continue

            handler(job)
            repo.complete(job["id"])
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    run_worker()
