from datetime import date
import hashlib
import json
from typing import Optional

from django.utils import timezone

from jobs.models import ScheduledJobExecution


def _build_payload_hash(payload: dict) -> str:
    serialized_payload = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized_payload.encode("utf-8")).hexdigest()


def create_pending_job(payload: dict) -> ScheduledJobExecution:
    snapshot_date = payload.get("snapshot_date")
    if isinstance(snapshot_date, str):
        snapshot_date = date.fromisoformat(snapshot_date)

    return ScheduledJobExecution.objects.create(
        job_key=payload["job_key"],
        job_type=payload["job_type"],
        tenant_id=payload.get("tenant_id", ""),
        company_id=payload.get("company_id", ""),
        scope_type=payload.get("scope_type", ""),
        scope_id=payload.get("scope_id", ""),
        project_id=payload.get("project_id", ""),
        period_year=payload.get("period_year"),
        period_month=payload.get("period_month"),
        snapshot_date=snapshot_date,
        priority=payload.get("priority", 5),
        status=ScheduledJobExecution.STATUS_PENDING,
        payload=payload,
        payload_hash=_build_payload_hash(payload),
    )

def mark_job_queued(job: ScheduledJobExecution, broker_message_id: Optional[str] = None) -> None:
    job.status = ScheduledJobExecution.STATUS_QUEUED
    job.queued_at = timezone.now()
    if broker_message_id:
        job.broker_message_id = broker_message_id
    job.save(update_fields=["status", "queued_at", "broker_message_id", "updated_at"])


def mark_job_failed(job: ScheduledJobExecution, error_message: str) -> None:
    job.status = ScheduledJobExecution.STATUS_FAILED
    job.finished_at = timezone.now()
    job.error_message = error_message
    job.save(update_fields=["status", "finished_at", "error_message", "updated_at"])


def job_already_open(job_key: str) -> bool:
    return ScheduledJobExecution.objects.filter(
        job_key=job_key,
        status__in=[
            ScheduledJobExecution.STATUS_PENDING,
            ScheduledJobExecution.STATUS_QUEUED,
            ScheduledJobExecution.STATUS_RUNNING,
        ],
    ).exists()


def get_job_by_key(job_key: str) -> ScheduledJobExecution:
    return ScheduledJobExecution.objects.get(job_key=job_key)


def mark_job_running(job: ScheduledJobExecution) -> None:
    job.status = ScheduledJobExecution.STATUS_RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at", "updated_at"])


def mark_job_succeeded(job: ScheduledJobExecution) -> None:
    job.status = ScheduledJobExecution.STATUS_SUCCEEDED
    job.finished_at = timezone.now()
    job.error_message = ""
    job.save(update_fields=["status", "finished_at", "error_message", "updated_at"])