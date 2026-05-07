from django.contrib import admin

from common.models import CompanyAccess


@admin.register(CompanyAccess)
class CompanyAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "tenant_id", "company_id", "updated_at")
    search_fields = ("user__username", "tenant_id", "company_id")
