from django.contrib import admin

from cloud.models import RawCostRecord


@admin.register(RawCostRecord)
class RawCostRecordAdmin(admin.ModelAdmin):
    list_display = (
        "tenant_id",
        "company_id",
        "area_id",
        "project_id",
        "service_name",
        "period_year",
        "period_month",
        "cost_amount",
        "currency",
    )
    search_fields = ("tenant_id", "company_id", "area_id", "project_id", "service_name")
    list_filter = ("period_year", "period_month", "currency", "service_name")