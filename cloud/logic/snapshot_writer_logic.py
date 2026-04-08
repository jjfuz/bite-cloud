from datetime import datetime
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from cloud.services.aws_cost_service import FinancialReportResult
from cloud.services.aws_ebs_service import OrphanEBSRecord
from reports.models import FinancialReportSnapshot, OrphanEBSSnapshot


@transaction.atomic
def replace_financial_report_snapshot(
    tenant_id: str,
    company_id: str,
    scope_type: str,
    scope_id: str,
    period_year: int,
    period_month: int,
    result: FinancialReportResult,
) -> FinancialReportSnapshot:
    FinancialReportSnapshot.objects.filter(
        tenant_id=tenant_id,
        scope_type=scope_type,
        scope_id=scope_id,
        period_year=period_year,
        period_month=period_month,
        report_type=FinancialReportSnapshot.REPORT_TYPE_MONTHLY,
        is_current=True,
    ).update(is_current=False)

    snapshot = FinancialReportSnapshot.objects.create(
        tenant_id=tenant_id,
        company_id=company_id,
        scope_type=scope_type,
        scope_id=scope_id,
        period_year=period_year,
        period_month=period_month,
        report_type=FinancialReportSnapshot.REPORT_TYPE_MONTHLY,
        currency=result.currency,
        total_cost=result.total_cost,
        report_payload={
            "breakdown": [
                {
                    "service": item.service,
                    "cost": str(item.cost),
                }
                for item in result.breakdown
            ],
            "raw_payload": result.raw_payload,
        },
        generated_at=timezone.now(),
        is_current=True,
    )
    return snapshot


@transaction.atomic
def replace_orphan_ebs_snapshot(
    tenant_id: str,
    company_id: str,
    project_id: str,
    snapshot_date,
    region: str,
    records: list[OrphanEBSRecord],
) -> None:
    OrphanEBSSnapshot.objects.filter(
        tenant_id=tenant_id,
        company_id=company_id,
        project_id=project_id,
        snapshot_date=snapshot_date,
    ).delete()

    now = timezone.now()

    snapshot_rows = []
    for position, record in enumerate(records, start=1):
        snapshot_rows.append(
            OrphanEBSSnapshot(
                tenant_id=tenant_id,
                company_id=company_id,
                project_id=project_id,
                snapshot_date=snapshot_date,
                volume_id=record.volume_id,
                volume_name=record.volume_name,
                region=region,
                volume_type=record.volume_type,
                size_gib=record.size_gib,
                monthly_cost=record.monthly_cost,
                currency="USD",
                ranking_position=position,
                details_payload=record.raw_payload,
                generated_at=now,
            )
        )

    if snapshot_rows:
        OrphanEBSSnapshot.objects.bulk_create(snapshot_rows)