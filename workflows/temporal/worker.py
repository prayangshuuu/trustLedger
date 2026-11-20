"""Temporal worker for the loan lifecycle.

    TEMPORAL_HOST=localhost:7233 TRUSTLEDGER_API_URL=http://localhost:8000 \
        uv run python -m workflows.temporal.worker
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from workflows.temporal.activities import LoanActivities
from workflows.temporal.shared import TASK_QUEUE
from workflows.temporal.workflow import LoanWorkflow


async def main() -> None:
    client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))
    activities = LoanActivities()
    with ThreadPoolExecutor(max_workers=8) as pool:
        worker = Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[LoanWorkflow],
            activities=activities.all(),
            activity_executor=pool,
        )
        print(f"worker listening on {TASK_QUEUE}")
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
