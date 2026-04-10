from django.contrib import admin
from django.urls import include, path
from jobs.views import job_detail_api
from .views import health, orphan_report_detail_json

from common.views import (
    dashboard_view,
    financial_snapshot_detail_view,
    health_view,
    job_detail_view,
    orphan_report_detail_view,
)

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("health/", health, name="health_json"), 
    path("health-check/", health_view, name="health_original"), 
    path("admin/", admin.site.urls),
    path("reports/", include("reports.urls")),
    
    path("dashboard/jobs/<int:job_id>/", job_detail_view, name="job-detail"),
    path("dashboard/financial-snapshots/<int:snapshot_id>/", financial_snapshot_detail_view, name="financial-snapshot-detail"),
    path("dashboard/orphan-ebs-reports/<int:sample_row_id>/", orphan_report_detail_view, name="orphan-report-detail"),
    
    path("api/jobs/<int:job_id>/", job_detail_api, name="job-detail-api"),
    path("api/v1/orphan-ebs/<int:sample_row_id>/json/", orphan_report_detail_json, name="orphan_ebs_json"),
]
