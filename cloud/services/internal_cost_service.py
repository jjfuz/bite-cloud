from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db.models import Sum

from cloud.models import RawCostRecord


@dataclass(frozen=True)
class FinancialBreakdownItem:
    service: str
    cost: Decimal


@dataclass(frozen=True)
class FinancialReportResult:
    total_cost: Decimal
    currency: str
    breakdown: list[FinancialBreakdownItem]
    raw_payload: dict[str, Any]


def build_monthly_financial_report_from_internal_data(
    tenant_id: str,
    company_id: str,
    scope_type: str,
    scope_id: str,
    period_year: int,
    period_month: int,
) -> FinancialReportResult:
    queryset = RawCostRecord.objects.filter(
        tenant_id=tenant_id,
        period_year=period_year,
        period_month=period_month,
    )

    if scope_type == "client":
        queryset = queryset.filter(company_id=scope_id)
    elif scope_type == "area":
        queryset = queryset.filter(area_id=scope_id)
    elif scope_type == "project":
        queryset = queryset.filter(project_id=scope_id)
    else:
        raise ValueError(f"Scope type no soportado: {scope_type}")

    grouped = (
        queryset.values("service_name", "currency")
        .annotate(total_service_cost=Sum("cost_amount"))
        .order_by("-total_service_cost", "service_name")
    )

    breakdown: list[FinancialBreakdownItem] = []
    total_cost = Decimal("0.00")
    currency = "USD"

    for row in grouped:
        amount = row["total_service_cost"] or Decimal("0.00")
        currency = row["currency"] or "USD"
        breakdown.append(
            FinancialBreakdownItem(
                service=row["service_name"],
                cost=amount,
            )
        )
        total_cost += amount

    return FinancialReportResult(
        total_cost=total_cost,
        currency=currency,
        breakdown=breakdown,
        raw_payload={
            "scope_type": scope_type,
            "scope_id": scope_id,
            "period_year": period_year,
            "period_month": period_month,
            "services_count": len(breakdown),
        },
    )