import json

from django.core.cache import cache
from django.db import DatabaseError
from django.db.models import Count, Max, Min
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from common.auth import get_request_scope
from jobs.models import ScheduledJobExecution
from reports.models import FinancialReportSnapshot, OrphanEBSSnapshot


def _pretty_json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _get_report_service_status():
    recovering_since = cache.get('orphan_ebs_recovering')
    if recovering_since:
        return {
            "status": "recovering",
            "message": "El servicio de reportes se está recuperando de una falla.",
            "recovering_since": recovering_since.isoformat(),
        }
    return {"status": "healthy"}


def health_view(request):
    return JsonResponse({"status": "ok"}, status=200)


def dashboard_view(request):
    dashboard_error_message = None
    total_jobs = 0
    open_jobs = 0
    failed_jobs = 0
    succeeded_jobs = 0
    latest_financial_snapshots = []
    latest_orphan_reports = []
    recent_jobs = []
    sample_orphan_url = None

    try:
        scope = get_request_scope(request)
        jobs_qs = ScheduledJobExecution.objects.filter(
            tenant_id=scope.tenant_id,
            company_id=scope.company_id,
        )
        financial_qs = FinancialReportSnapshot.objects.filter(
            tenant_id=scope.tenant_id,
            company_id=scope.company_id,
            is_current=True,
        )
        orphan_qs = OrphanEBSSnapshot.objects.filter(
            tenant_id=scope.tenant_id,
            company_id=scope.company_id,
        )

        total_jobs = jobs_qs.count()
        open_jobs = jobs_qs.filter(
            status__in=["PENDING", "QUEUED", "RUNNING"]
        ).count()
        failed_jobs = jobs_qs.filter(status="FAILED").count()
        succeeded_jobs = jobs_qs.filter(status="SUCCEEDED").count()

        latest_financial_snapshots = financial_qs.order_by("-generated_at")[:10]

        latest_orphan_reports = (
            orphan_qs.values(
                "tenant_id",
                "company_id",
                "project_id",
                "snapshot_date",
                "generated_at",
            )
            .annotate(
                total_orphan_volumes=Count("id"),
                max_monthly_cost=Max("monthly_cost"),
                sample_row_id=Min("id"),
            )
            .order_by("-generated_at")[:10]
        )

        recent_jobs = jobs_qs.order_by("-updated_at")[:15]

        latest_orphan_report = latest_orphan_reports[0] if latest_orphan_reports else None

        if latest_orphan_report:
            sample_orphan_url = (
                f"/reports/orphan-ebs/"
                f"{latest_orphan_report['project_id']}/"
                f"?snapshot_date={latest_orphan_report['snapshot_date']}"
            )
    except DatabaseError:
        dashboard_error_message = (
            "El dashboard no está disponible porque la base de datos no responde. "
            "Verifique el estado del servicio y vuelva a intentar."
        )

    report_service_status = _get_report_service_status()

    context = {
        "total_jobs": total_jobs,
        "open_jobs": open_jobs,
        "failed_jobs": failed_jobs,
        "succeeded_jobs": succeeded_jobs,
        "latest_financial_snapshots": latest_financial_snapshots,
        "latest_orphan_reports": latest_orphan_reports,
        "recent_jobs": recent_jobs,
        "sample_financial_url": "/reports/financial/project/company-001-project-001/?year=2026&month=4",
        "sample_orphan_url": sample_orphan_url,
        "report_service_status": report_service_status,
        "dashboard_error_message": dashboard_error_message,
    }
    return render(request, "common/dashboard.html", context)


def financial_snapshot_detail_view(request, snapshot_id: int):
    scope = get_request_scope(request)
    snapshot = get_object_or_404(
        FinancialReportSnapshot,
        id=snapshot_id,
        tenant_id=scope.tenant_id,
        company_id=scope.company_id,
    )

    payload = snapshot.report_payload or {}
    breakdown = payload.get("breakdown", [])
    raw_payload = payload.get("raw_payload", {})

    context = {
        "snapshot": snapshot,
        "breakdown": breakdown,
        "raw_payload_pretty": _pretty_json(raw_payload),
        "full_payload_pretty": _pretty_json(payload),
    }
    return render(request, "common/financial_snapshot_detail.html", context)


def orphan_report_detail_view(request, sample_row_id: int):
    scope = get_request_scope(request)
    sample_row = get_object_or_404(
        OrphanEBSSnapshot,
        id=sample_row_id,
        tenant_id=scope.tenant_id,
        company_id=scope.company_id,
    )

    rows = OrphanEBSSnapshot.objects.filter(
        tenant_id=sample_row.tenant_id,
        company_id=sample_row.company_id,
        project_id=sample_row.project_id,
        snapshot_date=sample_row.snapshot_date,
    ).order_by("ranking_position", "volume_id")

    items = [
        {
            "volume_id": row.volume_id,
            "volume_name": row.volume_name,
            "region": row.region,
            "volume_type": row.volume_type,
            "size_gib": row.size_gib,
            "monthly_cost": row.monthly_cost,
            "currency": row.currency,
            "ranking_position": row.ranking_position,
            "details_pretty": _pretty_json(row.details_payload or {}),
        }
        for row in rows
    ]

    context = {
        "sample_row": sample_row,
        "total_orphan_volumes": rows.count(),
        "items": items,
    }
    return render(request, "common/orphan_report_detail.html", context)


def job_detail_view(request, job_id: int):
    scope = get_request_scope(request)
    job = get_object_or_404(
        ScheduledJobExecution,
        id=job_id,
        tenant_id=scope.tenant_id,
        company_id=scope.company_id,
    )

    context = {
        "job": job,
        "payload_pretty": _pretty_json(job.payload or {}),
    }
    return render(request, "common/job_detail.html", context)