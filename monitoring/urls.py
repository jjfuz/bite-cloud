from django.contrib import admin
from django.urls import include, path
from jobs.views import job_detail_api

from common.views import (
    dashboard_view,
    financial_snapshot_detail_view,
    health_view,
    job_detail_view,
    orphan_report_detail_view,
)

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("health/", health_view, name="health"),
    path("admin/", admin.site.urls),
    path("reports/", include("reports.urls")),
    path("dashboard/jobs/<int:job_id>/", job_detail_view, name="job-detail"),
    path(
        "dashboard/financial-snapshots/<int:snapshot_id>/",
        financial_snapshot_detail_view,
        name="financial-snapshot-detail",
    ),
    path(
        "dashboard/orphan-ebs-reports/<int:sample_row_id>/",
        orphan_report_detail_view,
        name="orphan-report-detail",
    ),
    path("api/jobs/<int:job_id>/", job_detail_api, name="job-detail-api"),

]
