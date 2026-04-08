from calendar import monthrange
from datetime import date

from cloud.logic.snapshot_writer_logic import (
    replace_financial_report_snapshot,
    replace_orphan_ebs_snapshot,
)
from cloud.services.aws_cost_service import get_monthly_financial_report
from cloud.services.aws_ebs_service import list_orphan_ebs_for_project


class PermanentJobError(Exception):
    pass


class TransientJobError(Exception):
    pass


def _resolve_month_range(period_year: int, period_month: int) -> tuple[str, str]:
    start_date = date(period_year, period_month, 1)
    _, last_day = monthrange(period_year, period_month)
    end_date = date(period_year, period_month, last_day)

    # Cost Explorer usa TimePeriod end como exclusivo; pasamos primer día del siguiente mes.
    if period_month == 12:
        next_month = date(period_year + 1, 1, 1)
    else:
        next_month = date(period_year, period_month + 1, 1)

    return start_date.isoformat(), next_month.isoformat()


def handle_financial_report_job(payload: dict) -> None:
    try:
        tenant_id = payload["tenant_id"]
        company_id = payload["company_id"]
        scope_type = payload["scope_type"]
        scope_id = payload["scope_id"]
        period_year = int(payload["period_year"])
        period_month = int(payload["period_month"])
    except KeyError as exc:
        raise PermanentJobError(f"Payload financiero inválido. Falta el campo {exc}.") from exc

    period_start, period_end = _resolve_month_range(
        period_year=period_year,
        period_month=period_month,
    )

    project_id = scope_id if scope_type == "project" else None

    try:
        result = get_monthly_financial_report(
            period_start=period_start,
            period_end=period_end,
            project_id=project_id,
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
    except Exception as exc:
        raise TransientJobError("Falló la generación del snapshot financiero.") from exc


def handle_orphan_ebs_job(payload: dict, region: str) -> None:
    try:
        tenant_id = payload["tenant_id"]
        company_id = payload["company_id"]
        project_id = payload["project_id"]
        snapshot_date = date.fromisoformat(payload["snapshot_date"])
    except KeyError as exc:
        raise PermanentJobError(f"Payload orphan EBS inválido. Falta el campo {exc}.") from exc

    try:
        records = list_orphan_ebs_for_project(
            project_id=project_id,
            region=region,
        )
        replace_orphan_ebs_snapshot(
            tenant_id=tenant_id,
            company_id=company_id,
            project_id=project_id,
            snapshot_date=snapshot_date,
            region=region,
            records=records,
        )
    except Exception as exc:
        raise TransientJobError("Falló la generación del snapshot de volúmenes EBS huérfanos.") from exc