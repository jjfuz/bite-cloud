from django.contrib import admin

from reports.models import FinancialReportSnapshot, OrphanEBSSnapshot


@admin.register(FinancialReportSnapshot)
class FinancialReportSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "tenant_id",
        "scope_type",
        "scope_id",
        "period_year",
        "period_month",
        "total_cost",
        "generated_at",
        "is_current",
    )
    search_fields = ("tenant_id", "scope_id", "company_id")
    list_filter = ("scope_type", "period_year", "period_month", "is_current")


@admin.register(OrphanEBSSnapshot)
class OrphanEBSSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "tenant_id",
        "company_id",
        "project_id",
        "volume_id",
        "monthly_cost",
        "snapshot_date",
        "ranking_position",
    )
    search_fields = ("tenant_id", "project_id", "volume_id")
    list_filter = ("region", "snapshot_date")