from datetime import date


def build_financial_report_refresh_payload(
    tenant_id: str,
    company_id: str,
    scope_type: str,
    scope_id: str,
    period_year: int,
    period_month: int,
    priority: int = 5,
) -> dict:
    job_key = (
        f"financial_monthly:{tenant_id}:{scope_type}:{scope_id}:"
        f"{period_year}:{period_month}"
    )

    return {
        "job_type": "refresh_financial_report",
        "job_key": job_key,
        "tenant_id": tenant_id,
        "company_id": company_id,
        "scope_type": scope_type,
        "scope_id": scope_id,
        "period_year": period_year,
        "period_month": period_month,
        "report_type": "financial_monthly",
        "priority": priority,
    }


def build_orphan_ebs_refresh_payload(
    tenant_id: str,
    company_id: str,
    project_id: str,
    snapshot_date: date,
    priority: int = 3,
) -> dict:
    job_key = f"orphan_ebs:{tenant_id}:{company_id}:{project_id}:{snapshot_date.isoformat()}"

    return {
        "job_type": "refresh_orphan_ebs",
        "job_key": job_key,
        "tenant_id": tenant_id,
        "company_id": company_id,
        "project_id": project_id,
        "snapshot_date": snapshot_date.isoformat(),
        "priority": priority,
    }