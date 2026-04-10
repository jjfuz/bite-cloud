import json

from django.db.models import Count, Max, Min
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from jobs.models import ScheduledJobExecution
from reports.models import FinancialReportSnapshot, OrphanEBSSnapshot


def _pretty_json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def health_view(request):
    return JsonResponse({"status": "ok"}, status=200)


def dashboard_view(request):
    total_jobs = ScheduledJobExecution.objects.count()
    open_jobs = ScheduledJobExecution.objects.filter(
        status__in=["PENDING", "QUEUED", "RUNNING"]
    ).count()
    failed_jobs = ScheduledJobExecution.objects.filter(status="FAILED").count()
    succeeded_jobs = ScheduledJobExecution.objects.filter(status="SUCCEEDED").count()

    latest_financial_snapshots = FinancialReportSnapshot.objects.filter(
        is_current=True
    ).order_by("-generated_at")[:10]

    latest_orphan_reports = (
        OrphanEBSSnapshot.objects.values(
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

    recent_jobs = ScheduledJobExecution.objects.order_by("-updated_at")[:15]

    latest_orphan_report = latest_orphan_reports[0] if latest_orphan_reports else None

    if latest_orphan_report:
        sample_orphan_url = (
            f"/reports/orphan-ebs/"
            f"{latest_orphan_report['project_id']}/"
            f"?snapshot_date={latest_orphan_report['snapshot_date']}"
        )
    else:
        sample_orphan_url = None

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
    }
    return render(request, "common/dashboard.html", context)


def financial_snapshot_detail_view(request, snapshot_id: int):
    snapshot = get_object_or_404(FinancialReportSnapshot, id=snapshot_id)

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
    sample_row = get_object_or_404(OrphanEBSSnapshot, id=sample_row_id)

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
    job = get_object_or_404(ScheduledJobExecution, id=job_id)

    context = {
        "job": job,
        "payload_pretty": _pretty_json(job.payload or {}),
    }
    return render(request, "common/job_detail.html", context)