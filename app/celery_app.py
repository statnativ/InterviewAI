"""M5's execution model: Celery + Redis, this app's first real background-job
infra (BackgroundTasks — IA-003, candidate_judge.py's own trigger — was
deliberately not reused a third time here; see ADR-009).

The one thing that had to be gotten right: app.db's engine and
llm_client.get_http_client()'s httpx.AsyncClient are both lazy module-level
singletons that bind to whichever asyncio event loop is running the first
time they're used (this codebase already hit exactly this class of bug once
— Backend Overview's bug #12, pytest's per-test-function loop default). A
Celery worker process runs many tasks over its lifetime; a naive
asyncio.run() per task would tear down and recreate the loop every time,
breaking both singletons on the second task. The fix: one persistent event
loop per worker PROCESS (not per task), created once in worker_process_init
(fires after the prefork fork, so no fork-inherited-connection risk) and
reused for every task that process ever runs — app.db.engine/async_session
and llm_client's shared client both then stay bound to one stable loop for
the worker's whole life, unmodified, no per-service special-casing needed.

No result backend configured — nothing queries Celery's own task-result
store; interview_evaluator.py persists everything to Postgres directly, and
app/routers/interview_reports.py polls that, matching this codebase's
"state lives in the database, not the queue" discipline (IA-003's
BackgroundTasks + polling precedent).
"""
import asyncio
import uuid

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

from app.config import settings
from app.db import engine

celery_app = Celery("interview_agent", broker=settings.redis_url)

_loop: asyncio.AbstractEventLoop | None = None


@worker_process_init.connect
def _init_worker(**kwargs) -> None:
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)


@worker_process_shutdown.connect
def _shutdown_worker(**kwargs) -> None:
    if _loop is not None:
        _loop.run_until_complete(engine.dispose())
        _loop.close()


@celery_app.task(name="evaluate_interview_task")
def evaluate_interview_task(session_id: str) -> None:
    from app.services.interview_evaluator import evaluate_interview

    _loop.run_until_complete(evaluate_interview(uuid.UUID(session_id)))
