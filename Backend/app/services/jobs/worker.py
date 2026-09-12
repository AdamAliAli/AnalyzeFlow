"""Standalone worker: `python -m app.services.jobs.worker`.

Only needed when JOB_RUNNER=worker. With JOB_RUNNER=inline (the default) the
API process runs analysis in a FastAPI BackgroundTask, which is enough for
development and for the demo.

Use the worker when the API is on a host that kills long requests, or when
you want analysis load off the web process.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import AsyncSessionLocal
from app.services.analysis.pipeline import run_analysis
from app.services.jobs.queue import claim_next

logger = get_logger(__name__)
_shutdown = asyncio.Event()


async def _loop() -> None:
    logger.info(
        "Worker started (poll every %.1fs)", settings.job_poll_interval_seconds
    )
    while not _shutdown.is_set():
        picked_up = False
        async with AsyncSessionLocal() as db:
            job = await claim_next(db)
            if job is not None:
                picked_up = True
                logger.info("Picked up job %s", job.public_id)
                await run_analysis(db, job.analysis_job_id)

        if not picked_up:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(
                    _shutdown.wait(), timeout=settings.job_poll_interval_seconds
                )
    logger.info("Worker stopped")


def main() -> None:
    configure_logging()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, _shutdown.set)

    try:
        loop.run_until_complete(_loop())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
