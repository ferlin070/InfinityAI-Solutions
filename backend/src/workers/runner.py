import time
import os
import signal
from src.core.config import logger
from src.db.repositories.jobs import JobRepo
from src.workers.handlers import process_inbound, generate_quotation, daily_briefing

HANDLERS = {
    "process_inbound": process_inbound,
    "generate_quotation": generate_quotation,
    "daily_briefing": daily_briefing,
}

JOB_TIMEOUT = int(os.getenv("WORKER_JOB_TIMEOUT", "180"))


class JobTimeout(Exception):
    pass


def _timeout_handler(signum, frame):
    raise JobTimeout("Job handler timed out")


def run_worker():
    logger.info("Worker started — polling for jobs...")
    repo = JobRepo()
    signal.signal(signal.SIGALRM, _timeout_handler)
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

            signal.alarm(JOB_TIMEOUT)
            try:
                handler(job)
                signal.alarm(0)
                repo.complete(job["id"])
            except JobTimeout:
                logger.error(f"Job {job['id']} timed out after {JOB_TIMEOUT}s")
                signal.alarm(0)
                try:
                    repo.fail(job["id"], f"Handler timed out after {JOB_TIMEOUT}s")
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            signal.alarm(0)
            try:
                repo.fail(job["id"], str(e))
            except Exception:
                pass
            time.sleep(5)


if __name__ == "__main__":
    run_worker()
