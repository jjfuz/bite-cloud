from decimal import Decimal
from django.utils import timezone

from cloud.logic.snapshot_writer_logic import (
    replace_financial_report_snapshot,
    replace_orphan_ebs_snapshot,
)
from cloud.services.aws_cost_service import FinancialBreakdownItem, FinancialReportResult
from cloud.services.aws_ebs_service import OrphanEBSRecord

from datetime import date

# ...

def handle_fake_financial_report_job(payload: dict) -> None:
    tenant_id = payload["tenant_id"]
    company_id = payload["company_id"]
    scope_type = payload["scope_type"]
    scope_id = payload["scope_id"]
    period_year = int(payload["period_year"])
    period_month = int(payload["period_month"])


    result = FinancialReportResult(
        total_cost=Decimal("1842.33"),
        currency="USD",
        breakdown=[
            FinancialBreakdownItem(service="Amazon EC2", cost=Decimal("922.11")),
            FinancialBreakdownItem(service="Amazon EBS", cost=Decimal("301.05")),
            FinancialBreakdownItem(service="Amazon RDS", cost=Decimal("619.17")),
        ],
        raw_payload={
            "source": "fake-local-data",
            "generated_at": timezone.now().isoformat(),
        },
    )

    replace_financial_report_snapshot(
        tenant_id=tenant_id,
        company_id=company_id,
        scope_type=scope_type,
        scope_id=scope_id,
        period_year=period_year,
        period_month=period_month,
        result=result,
    )


def handle_fake_orphan_ebs_job(payload: dict, region: str) -> None:
    tenant_id = payload["tenant_id"]
    company_id = payload["company_id"]
    project_id = payload["project_id"]
    snapshot_date = date.fromisoformat(payload["snapshot_date"])


    records = [
        OrphanEBSRecord(
            volume_id="vol-001",
            volume_name="orphan-data-1",
            region=region,
            volume_type="gp3",
            size_gib=500,
            monthly_cost=Decimal("40.00"),
            project_id=project_id,
            raw_payload={"source": "fake-local-data", "status": "available"},
        ),
        OrphanEBSRecord(
            volume_id="vol-002",
            volume_name="orphan-logs-1",
            region=region,
            volume_type="gp2",
            size_gib=200,
            monthly_cost=Decimal("20.00"),
            project_id=project_id,
            raw_payload={"source": "fake-local-data", "status": "available"},
        ),
        OrphanEBSRecord(
            volume_id="vol-003",
            volume_name="orphan-backup-1",
            region=region,
            volume_type="sc1",
            size_gib=1000,
            monthly_cost=Decimal("25.00"),
            project_id=project_id,
            raw_payload={"source": "fake-local-data", "status": "available"},
        ),
    ]

    records.sort(key=lambda item: (-item.monthly_cost, item.volume_id))

    replace_orphan_ebs_snapshot(
        tenant_id=tenant_id,
        company_id=company_id,
        project_id=project_id,
        snapshot_date=snapshot_date,
        region=region,
        records=records,
    )