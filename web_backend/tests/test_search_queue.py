import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from vercel.queue import ALL_DEPLOYMENTS

from web_backend.app.search_queue import SEARCH_JOBS, SearchJob, enqueue_search_job


class SearchQueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_enqueue_uses_global_deployment_and_run_idempotency(self):
        run_id = uuid4()
        job = SearchJob(user_id=uuid4(), run_id=run_id)
        queue = SimpleNamespace(send=AsyncMock(return_value="message-id"))

        with patch("web_backend.app.search_queue.create_search_queue", return_value=queue) as create_queue:
            result = await enqueue_search_job("iad1", job)

        create_queue.assert_called_once_with("iad1")
        queue.send.assert_awaited_once_with(
            SEARCH_JOBS,
            job,
            deployment=ALL_DEPLOYMENTS,
            retention=timedelta(days=7),
            idempotency_key=str(run_id),
        )
        self.assertEqual(result, "message-id")
        self.assertNotIn("access_token", job.model_dump())
