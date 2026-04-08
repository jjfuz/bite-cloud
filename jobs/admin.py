from django.contrib import admin

from jobs.models import ScheduledJobExecution, SchedulerLock


@admin.register(ScheduledJobExecution)
class ScheduledJobExecutionAdmin(admin.ModelAdmin):
    list_display = (
        "job_type",
        "job_key",
        "tenant_id",
        "status",
        "priority",
        "requested_at",
        "queued_at",
        "finished_at",
    )
    search_fields = ("job_key", "tenant_id", "scope_id", "project_id")
    list_filter = ("job_type", "status", "priority")


@admin.register(SchedulerLock)
class SchedulerLockAdmin(admin.ModelAdmin):
    list_display = ("name", "locked_by", "locked_until", "updated_at")
    search_fields = ("name", "locked_by")