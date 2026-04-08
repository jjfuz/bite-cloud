from typing import Any

from django.core.exceptions import ObjectDoesNotExist

from reports.models import FinancialReportSnapshot


def get_financial_report_snapshot(
    tenant_id: str,
    scope_type: str,
    scope_id: str,
    period_year: int,
    period_month: int,
) -> FinancialReportSnapshot:
    try:
        return FinancialReportSnapshot.objects.get(
            tenant_id=tenant_id,
            scope_type=scope_type,
            scope_id=scope_id,
            period_year=period_year,
            period_month=period_month,
            report_type=FinancialReportSnapshot.REPORT_TYPE_MONTHLY,
            is_current=True,
        )
    except ObjectDoesNotExist as exc:
        raise ValueError("No existe un snapshot financiero vigente para los parámetros dados.") from exc


def serialize_financial_report(snapshot: FinancialReportSnapshot) -> dict[str, Any]:
    return {
        "tenant_id": snapshot.tenant_id,
        "company_id": snapshot.company_id,
        "scope_type": snapshot.scope_type,
        "scope_id": snapshot.scope_id,
        "period_year": snapshot.period_year,
        "period_month": snapshot.period_month,
        "report_type": snapshot.report_type,
        "currency": snapshot.currency,
        "total_cost": str(snapshot.total_cost),
        "generated_at": snapshot.generated_at.isoformat(),
        "payload": snapshot.report_payload,
    }