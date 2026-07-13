"""Background task submission.

For the MVP this is a single-process ThreadPoolExecutor rather than a real
Celery + Redis broker deployment — same role in the architecture (claims
intake hands off to a background worker so the HTTP request returns
immediately), just without the extra infra to stand up locally. Swapping this
module for a `@celery_app.task` wrapper around `execute_claim_workflow` is a
drop-in change when moving to production infra.
"""

import logging
from concurrent.futures import ThreadPoolExecutor

from app.workflow.graph import execute_claim_workflow

logger = logging.getLogger("claims.worker")

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="claims-worker")


def _run_safely(claim_id: int) -> None:
    try:
        execute_claim_workflow(claim_id)
    except Exception:
        logger.exception("Unhandled error processing claim %s", claim_id)


def submit_claim_processing(claim_id: int) -> None:
    _executor.submit(_run_safely, claim_id)
