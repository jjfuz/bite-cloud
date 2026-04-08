from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from cloud.services.aws_session_service import build_cost_explorer_client


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


def get_monthly_financial_report(
    period_start: str,
    period_end: str,
    project_id: str | None = None,
) -> FinancialReportResult:
    ce_client = build_cost_explorer_client()

    request_params: dict[str, Any] = {
        "TimePeriod": {
            "Start": period_start,
            "End": period_end,
        },
        "Granularity": "MONTHLY",
        "Metrics": ["UnblendedCost"],
        "GroupBy": [{"Type": "DIMENSION", "Key": "SERVICE"}],
    }

    if project_id:
        request_params["Filter"] = {
            "Tags": {
                "Key": "ProjectId",
                "Values": [project_id],
                "MatchOptions": ["EQUALS"],
            }
        }

    response = ce_client.get_cost_and_usage(**request_params)

    results = response.get("ResultsByTime", [])
    if not results:
        return FinancialReportResult(
            total_cost=Decimal("0.00"),
            currency="USD",
            breakdown=[],
            raw_payload=response,
        )

    current_result = results[0]
    groups = current_result.get("Groups", [])

    breakdown: list[FinancialBreakdownItem] = []
    total_cost = Decimal("0.00")
    currency = "USD"

    for group in groups:
        keys = group.get("Keys", [])
        service_name = keys[0] if keys else "Unknown"

        amount_info = group.get("Metrics", {}).get("UnblendedCost", {})
        amount = Decimal(amount_info.get("Amount", "0"))
        currency = amount_info.get("Unit", "USD")

        breakdown.append(
            FinancialBreakdownItem(
                service=service_name,
                cost=amount,
            )
        )
        total_cost += amount

    breakdown.sort(key=lambda item: (-item.cost, item.service))

    return FinancialReportResult(
        total_cost=total_cost,
        currency=currency,
        breakdown=breakdown,
        raw_payload=response,
    )