"""Run tracking in raw.ingestion_runs. Each run gets a UUID, timing, status, and counts."""

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Connection, Engine, text

from foodie_collector.ingestion.raw_loader import LoadCounts
from foodie_collector.models import Rejection

logger = logging.getLogger(__name__)

MAX_ERROR_LENGTH = 2000


@dataclass
class RunStats:
    run_id: UUID = field(default_factory=uuid4)
    received: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    rejected: int = 0

    def add(self, counts: LoadCounts) -> None:
        self.inserted += counts.inserted
        self.updated += counts.updated
        self.unchanged += counts.unchanged

    def as_log_fields(self) -> dict[str, Any]:
        return {
            "run_id": str(self.run_id),
            "received": self.received,
            "inserted": self.inserted,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "rejected": self.rejected,
        }


def _finish(engine: Engine, stats: RunStats, status: str, error: str | None = None) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("""
                UPDATE raw.ingestion_runs
                SET status = :status, finished_at = now(), error_message = :error,
                    received_count = :received, inserted_count = :inserted, updated_count = :updated,
                    unchanged_count = :unchanged, rejected_count = :rejected
                WHERE run_id = :run_id
            """),
            {"status": status, "error": error, **stats.as_log_fields()},
        )


@contextmanager
def tracked_run(
    engine: Engine, source: str, target: str, parameters: dict[str, Any] | None = None
) -> Iterator[RunStats]:
    """Record a run as 'running' (committed immediately), then 'succeeded' or 'failed'.

    The run row is committed before any data work so failed runs stay visible even though the
    data transaction itself rolls back.
    """
    stats = RunStats()
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO raw.ingestion_runs (run_id, source, target, status, parameters)
                VALUES (:run_id, :source, :target, 'running', CAST(:parameters AS JSONB))
            """),
            {
                "run_id": stats.run_id,
                "source": source,
                "target": target,
                "parameters": json.dumps(parameters or {}, default=str),
            },
        )
    log_context = {"source": source, "target": target, "run_id": str(stats.run_id)}
    logger.info("ingestion run started", extra=log_context)
    try:
        yield stats
    except Exception as error:
        message = f"{type(error).__name__}: {error}"[:MAX_ERROR_LENGTH]
        _finish(engine, stats, "failed", message)
        logger.exception("ingestion run failed", extra={**log_context, "error": message})
        raise
    _finish(engine, stats, "succeeded")
    logger.info("ingestion run succeeded", extra={**log_context, **stats.as_log_fields()})


def record_rejections(connection: Connection, run_id: UUID, source: str, rejections: list[Rejection]) -> int:
    if rejections:
        connection.execute(
            text("""
                INSERT INTO raw.rejected_records (run_id, source, source_record_id, reason, payload)
                VALUES (:run_id, :source, :source_record_id, :reason, CAST(:payload AS JSONB))
            """),
            [
                {
                    "run_id": run_id,
                    "source": source,
                    "source_record_id": rejection.source_record_id,
                    "reason": rejection.reason,
                    "payload": json.dumps(rejection.payload, default=str),
                }
                for rejection in rejections
            ],
        )
    return len(rejections)
