from datetime import date

from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from reports.logic.orphan_resources_logic import (
    get_orphan_ebs_snapshot,
    serialize_orphan_ebs_snapshot,
)
from reports.logic.reports_logic import (
    get_financial_report_snapshot,
    serialize_financial_report,
)


def _get_current_tenant_id(request) -> str:
    return request.headers.get("X-Tenant-Id", "tenant-demo")


def _infer_company_id_from_project_id(project_id: str) -> str:
    parts = project_id.split("-")
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"
    return "company-demo"


def _resolve_company_id(request, project_id: str) -> str:
    return request.headers.get(
        "X-Company-Id",
        _infer_company_id_from_project_id(project_id),
    )


@require_GET
def get_financial_report_view(request, scope_type: str, scope_id: str):
    tenant_id = _get_current_tenant_id(request)
    period_year = int(request.GET.get("year"))
    period_month = int(request.GET.get("month"))

    try:
        snapshot = get_financial_report_snapshot(
            tenant_id=tenant_id,
            scope_type=scope_type,
            scope_id=scope_id,
            period_year=period_year,
            period_month=period_month,
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=404)

    return JsonResponse(serialize_financial_report(snapshot), status=200)


@require_GET
def get_orphan_ebs_view(request, project_id: str):
    tenant_id = _get_current_tenant_id(request)
    company_id = _resolve_company_id(request, project_id)

    snapshot_date_param = request.GET.get("snapshot_date")
    snapshot_date = date.fromisoformat(snapshot_date_param) if snapshot_date_param else date.today()

    try:
        records = get_orphan_ebs_snapshot(
            tenant_id=tenant_id,
            company_id=company_id,
            project_id=project_id,
            snapshot_date=snapshot_date,
        )
        cache.delete('orphan_ebs_recovering')
        return JsonResponse(serialize_orphan_ebs_snapshot(records), status=200)
    except Exception as e:
        if not cache.get('orphan_ebs_recovering'):
            cache.set('orphan_ebs_recovering', timezone.now())
        return JsonResponse({"error": "El servicio de reportes se está recuperando de una falla en la base de datos."}, status=503)
        


@require_GET
def get_reports_status_view(request):
    recovering_since = cache.get('orphan_ebs_recovering')
    if recovering_since:
        return JsonResponse({
            "status": "recovering",
            "message": "El servicio de reportes se está recuperando de una falla en la base de datos.",
            "recovering_since": recovering_since.isoformat()
        }, status=503)
    else:
        return JsonResponse({"status": "healthy"}, status=200)