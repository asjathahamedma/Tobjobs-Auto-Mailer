import asyncio
import logging

from vercel.queue import Message, subscribe

from web_backend.app.main import SearchFailedPermanently, _execute_search
from web_backend.app.search_queue import SEARCH_JOBS, SearchJob, create_search_queue
from web_backend.app.settings import get_settings

logger = logging.getLogger("topjobs_search_worker")
MAX_SEARCH_ATTEMPTS = 5


@subscribe(
    topic=SEARCH_JOBS,
    consumer_group="topjobs-search-worker",
    retry_after=60,
    max_attempts=MAX_SEARCH_ATTEMPTS,
)
async def process_search(message: Message[SearchJob]) -> None:
    job = message.payload
    attempt = message.metadata.delivery_count
    try:
        await asyncio.to_thread(
            _execute_search,
            str(job.user_id),
            str(job.run_id),
            str(job.resume_id) if job.resume_id else None,
            service_role=True,
            delivery_attempt=attempt,
            max_attempts=MAX_SEARCH_ATTEMPTS,
        )
    except SearchFailedPermanently:
        logger.exception("Search run %s failed after %s attempts", job.run_id, attempt)


async def run() -> None:
    settings = get_settings()
    queue = create_search_queue(settings.vercel_queue_region)
    await queue.poll_and_handle(process_search, interval=1, lease_duration=300)


if __name__ == "__main__":
    asyncio.run(run())
