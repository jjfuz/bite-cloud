import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

from django.utils import timezone

from jobs.broker.payload_builders import (
    build_financial_report_refresh_payload,
    build_orphan_ebs_refresh_payload,
)
from jobs.broker.publisher import BrokerPublisherError, publish_job
from jobs.logic.job_registry_logic import (
    create_pending_job,
    job_already_open,
    mark_job_failed,
    mark_job_queued,
)
from reports.models import FinancialReportSnapshot, OrphanEBSSnapshot

logger = logging.getLogger(__name__)

FINANCIAL_REFRESH_MAX_AGE_SECONDS = 30
ORPHAN_EBS_REFRESH_MAX_AGE_SECONDS = 30


@dataclass(frozen=True)
class FinancialScope:
    tenant_id: str
    company_id: str
    scope_type: str
    scope_id: str


@dataclass(frozen=True)
class OrphanEBSScope:
    tenant_id: str
    company_id: str
    project_id: str


def collect_active_financial_scopes() -> Iterable[FinancialScope]:
    scopes = []

    for company_number in range(1, 40):  # 40 scopes financieros
        company_id = f"company-{company_number:03d}"
        scopes.append(
            FinancialScope(
                tenant_id="tenant-demo",
                company_id=company_id,
                scope_type="project",
                scope_id=f"{company_id}-project-001",
            )
        )

    return scopes


def collect_active_orphan_ebs_scopes() -> Iterable[OrphanEBSScope]:
    scopes = []

    for company_number in range(1, 40):
        company_id = f"company-{company_number:03d}"
        scopes.append(
            OrphanEBSScope(
                tenant_id="tenant-demo",
                company_id=company_id,
                project_id=f"{company_id}-project-001",
            )
        )

    return scopes

def financial_snapshot_needs_refresh(
    tenant_id: str,
    scope_type: str,
    scope_id: str,
    period_year: int,
    period_month: int,
    max_age_seconds: int,
) -> bool:
    snapshot = FinancialReportSnapshot.objects.filter(
        tenant_id=tenant_id,
        scope_type=scope_type,
        scope_id=scope_id,
        period_year=period_year,
        period_month=period_month,
        report_type=FinancialReportSnapshot.REPORT_TYPE_MONTHLY,
        is_current=True,
    ).order_by("-generated_at").first()

    if snapshot is None:
        return True

    age = timezone.now() - snapshot.generated_at
    return age > timedelta(seconds=max_age_seconds)


def orphan_ebs_snapshot_needs_refresh(
    tenant_id: str,
    company_id: str,
    project_id: str,
    snapshot_date: date,
    max_age_seconds: int,
) -> bool:
    snapshot = OrphanEBSSnapshot.objects.filter(
        tenant_id=tenant_id,
        company_id=company_id,
        project_id=project_id,
        snapshot_date=snapshot_date,
    ).order_by("-generated_at").first()

    if snapshot is None:
        return True

    age = timezone.now() - snapshot.generated_at
    return age > timedelta(seconds=max_age_seconds)


def enqueue_financial_report_refresh(
    scope: FinancialScope,
    period_year: int,
    period_month: int,
) -> None:
    payload = build_financial_report_refresh_payload(
        tenant_id=scope.tenant_id,
        company_id=scope.company_id,
        scope_type=scope.scope_type,
        scope_id=scope.scope_id,
        period_year=period_year,
        period_month=period_month,
    )

    if job_already_open(payload["job_key"]):
        logger.info(
            "Skipping duplicated financial job because another one is still open. job_key=%s",
            payload["job_key"],
        )
        return

    job = create_pending_job(payload)

    try:
        broker_message_id = publish_job(payload)
        mark_job_queued(job, broker_message_id=broker_message_id)
        logger.info("Financial refresh job queued successfully. job_key=%s", payload["job_key"])
    except BrokerPublisherError as exc:
        logger.exception("Failed to queue financial refresh job. job_key=%s", payload["job_key"])
        mark_job_failed(job, str(exc))


def enqueue_orphan_ebs_refresh(scope: OrphanEBSScope, snapshot_date: date) -> None:
    payload = build_orphan_ebs_refresh_payload(
        tenant_id=scope.tenant_id,
        company_id=scope.company_id,
        project_id=scope.project_id,
        snapshot_date=snapshot_date,
    )

    if job_already_open(payload["job_key"]):
        logger.info(
            "Skipping duplicated orphan EBS job because another one is still open. job_key=%s",
            payload["job_key"],
        )
        return

    job = create_pending_job(payload)

    try:
        broker_message_id = publish_job(payload)
        mark_job_queued(job, broker_message_id=broker_message_id)
        logger.info("Orphan EBS refresh job queued successfully. job_key=%s", payload["job_key"])
    except BrokerPublisherError as exc:
        logger.exception("Failed to queue orphan EBS refresh job. job_key=%s", payload["job_key"])
        mark_job_failed(job, str(exc))


def run_scheduler_cycle() -> None:
    now = timezone.now()
    current_year = now.year
    current_month = now.month
    today = now.date()

    logger.info(
        "Starting scheduler cycle for period=%s-%s and snapshot_date=%s",
        current_year,
        current_month,
        today,
    )

    for scope in collect_active_financial_scopes():
        if financial_snapshot_needs_refresh(
            tenant_id=scope.tenant_id,
            scope_type=scope.scope_type,
            scope_id=scope.scope_id,
            period_year=current_year,
            period_month=current_month,
            max_age_seconds=FINANCIAL_REFRESH_MAX_AGE_SECONDS,
        ):
            logger.info(
                "Financial snapshot needs refresh. tenant_id=%s scope_type=%s scope_id=%s",
                scope.tenant_id,
                scope.scope_type,
                scope.scope_id,
            )
            enqueue_financial_report_refresh(
                scope=scope,
                period_year=current_year,
                period_month=current_month,
            )
        else:
            logger.info(
                "Financial snapshot is still fresh. tenant_id=%s scope_type=%s scope_id=%s",
                scope.tenant_id,
                scope.scope_type,
                scope.scope_id,
            )

    for scope in collect_active_orphan_ebs_scopes():
        if orphan_ebs_snapshot_needs_refresh(
            tenant_id=scope.tenant_id,
            company_id=scope.company_id,
            project_id=scope.project_id,
            snapshot_date=today,
            max_age_seconds=ORPHAN_EBS_REFRESH_MAX_AGE_SECONDS,
        ):
            logger.info(
                "Orphan EBS snapshot needs refresh. tenant_id=%s company_id=%s project_id=%s",
                scope.tenant_id,
                scope.company_id,
                scope.project_id,
            )
            enqueue_orphan_ebs_refresh(scope=scope, snapshot_date=today)
        else:
            logger.info(
                "Orphan EBS snapshot is still fresh. tenant_id=%s company_id=%s project_id=%s",
                scope.tenant_id,
                scope.company_id,
                scope.project_id,
            )

    logger.info("Scheduler cycle finished successfully.")