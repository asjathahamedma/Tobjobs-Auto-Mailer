from datetime import timedelta
from uuid import UUID

from pydantic import BaseModel
from vercel.queue import ALL_DEPLOYMENTS, QueueClient, Topic


class SearchJob(BaseModel):
    user_id: UUID
    run_id: UUID
    resume_id: UUID | None = None


SEARCH_JOBS = Topic[SearchJob]("topjobs-search-runs")


def create_search_queue(region: str) -> QueueClient:
    return QueueClient(region=region, deployment=ALL_DEPLOYMENTS)


async def enqueue_search_job(region: str, job: SearchJob) -> str | None:
    queue = create_search_queue(region)
    return await queue.send(
        SEARCH_JOBS,
        job,
        deployment=ALL_DEPLOYMENTS,
        retention=timedelta(days=7),
        idempotency_key=str(job.run_id),
    )
