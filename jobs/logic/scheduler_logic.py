import logging
from dataclasses import dataclass
from datetime import date
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
from jobs.logic.scheduler_lock_logic import acquire_scheduler_lock, release_scheduler_lock
from reports.models import FinancialReportSnapshot, OrphanEBSSnapshot

logger = logging.getLogger(__name__)


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
    """
    Placeholder inicial.
    Luego esto debe salir de una tabla real de tenants/proyectos/áreas habilitadas.
    """
    return [
        FinancialScope(
            tenant_id="tenant-demo",
            company_id="company-demo",
            scope_type="project",
            scope_id="project-001",
        ),
    ]


def collect_active_orphan_ebs_scopes() -> Iterable[OrphanEBSScope]:
    return [
        OrphanEBSScope(
            tenant_id="tenant-demo",
            company_id="company-demo",
            project_id="project-001",
        ),
    ]


def financial_snapshot_is_current(
    tenant_id: str,
    scope_type: str,
    scope_id: str,
    period_year: int,
    period_month: int,
) -> bool:
    return FinancialReportSnapshot.objects.filter(
        tenant_id=tenant_id,
        scope_type=scope_type,
        scope_id=scope_id,
        period_year=period_year,
        period_month=period_month,
        report_type=FinancialReportSnapshot.REPORT_TYPE_MONTHLY,
        is_current=True,
    ).exists()


def orphan_ebs_snapshot_exists(
    tenant_id: str,
    company_id: str,
    project_id: str,
    snapshot_date: date,
) -> bool:
    return OrphanEBSSnapshot.objects.filter(
        tenant_id=tenant_id,
        company_id=company_id,
        project_id=project_id,
        snapshot_date=snapshot_date,
    ).exists()


def enqueue_financial_report_refresh(scope: FinancialScope, period_year: int, period_month: int) -> None:
    payload = build_financial_report_refresh_payload(
        tenant_id=scope.tenant_id,
        company_id=scope.company_id,
        scope_type=scope.scope_type,
        scope_id=scope.scope_id,
        period_year=period_year,
        period_month=period_month,
    )

    if job_already_open(payload["job_key"]):
        logger.info("Skipping duplicated financial job job_key=%s", payload["job_key"])
        return

    job = create_pending_job(payload)

    try:
        broker_message_id = publish_job(payload)
        mark_job_queued(job, broker_message_id=broker_message_id)
    except BrokerPublisherError as exc:
        mark_job_failed(job, str(exc))


def enqueue_orphan_ebs_refresh(scope: OrphanEBSScope, snapshot_date: date) -> None:
    payload = build_orphan_ebs_refresh_payload(
        tenant_id=scope.tenant_id,
        company_id=scope.company_id,
        project_id=scope.project_id,
        snapshot_date=snapshot_date,
    )

    if job_already_open(payload["job_key"]):
        logger.info("Skipping duplicated orphan EBS job job_key=%s", payload["job_key"])
        return

    job = create_pending_job(payload)

    try:
        broker_message_id = publish_job(payload)
        mark_job_queued(job, broker_message_id=broker_message_id)
    except BrokerPublisherError as exc:
        mark_job_failed(job, str(exc))


def run_scheduler_cycle(lock_name: str = "global_scheduler_lock", locked_by: str = "scheduler-node") -> None:
    acquired = acquire_scheduler_lock(lock_name=lock_name, locked_by=locked_by)

    if not acquired:
        logger.info("Scheduler lock not acquired. Another node is leading this cycle.")
        return

    try:
        now = timezone.now()
        current_year = now.year
        current_month = now.month
        today = now.date()

        for scope in collect_active_financial_scopes():
            if not financial_snapshot_is_current(
                tenant_id=scope.tenant_id,
                scope_type=scope.scope_type,
                scope_id=scope.scope_id,
                period_year=current_year,
                period_month=current_month,
            ):
                enqueue_financial_report_refresh(
                    scope=scope,
                    period_year=current_year,
                    period_month=current_month,
                )

        for scope in collect_active_orphan_ebs_scopes():
            if not orphan_ebs_snapshot_exists(
                tenant_id=scope.tenant_id,
                company_id=scope.company_id,
                project_id=scope.project_id,
                snapshot_date=today,
            ):
                enqueue_orphan_ebs_refresh(scope=scope, snapshot_date=today)

    finally:
        release_scheduler_lock(lock_name=lock_name, locked_by=locked_by)