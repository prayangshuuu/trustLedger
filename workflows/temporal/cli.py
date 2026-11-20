"""Start and drive a loan workflow for a demo persona.

uv run python -m workflows.temporal.cli start --persona moon --amount 15000
uv run python -m workflows.temporal.cli repay loan-<id>
uv run python -m workflows.temporal.cli status loan-<id>
uv run python -m workflows.temporal.cli review loan-<id> --approve
"""

import argparse
import asyncio
import json
import os
import uuid

import httpx
from temporalio.client import Client

from workflows.temporal.shared import TASK_QUEUE, LoanInput
from workflows.temporal.workflow import LoanWorkflow


def persona_user_id(persona: str) -> str:
    resp = httpx.get(
        os.getenv("TRUSTLEDGER_API_URL", "http://localhost:8000") + "/demo/personas",
        headers={"X-API-Key": os.getenv("TRUSTLEDGER_API_KEY", "")},
        timeout=15,
    )
    resp.raise_for_status()
    for p in resp.json():
        if p["key"] == persona:
            return str(p["user_id"])
    raise SystemExit(f"persona '{persona}' not found (is the API seeded with DEMO_MODE=true?)")


async def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    start = sub.add_parser("start")
    start.add_argument("--persona", default="moon")
    start.add_argument("--user-id")
    start.add_argument("--amount", type=float, default=15000.0)
    start.add_argument("--interval-days", type=int, default=30)
    for name in ("repay", "status"):
        sub.add_parser(name).add_argument("workflow_id")
    review = sub.add_parser("review")
    review.add_argument("workflow_id")
    review.add_argument("--approve", action="store_true")
    args = parser.parse_args()

    client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))
    if args.cmd == "start":
        user_id = args.user_id or persona_user_id(args.persona)
        wf_id = f"loan-{uuid.uuid4().hex[:10]}"
        await client.start_workflow(
            LoanWorkflow.run,
            LoanInput(user_id=user_id, amount_bdt=args.amount, interval_days=args.interval_days),
            id=wf_id,
            task_queue=TASK_QUEUE,
        )
        print(wf_id)
        return
    handle = client.get_workflow_handle(args.workflow_id)
    if args.cmd == "repay":
        await handle.signal(LoanWorkflow.repay)
    elif args.cmd == "review":
        await handle.signal(LoanWorkflow.review, args.approve)
    print(json.dumps(await handle.query(LoanWorkflow.status), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
