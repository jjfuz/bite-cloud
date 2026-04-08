from django.db import models
from django.utils import timezone


class ScheduledJobExecution(models.Model):
    JOB_REFRESH_FINANCIAL_REPORT = "refresh_financial_report"
    JOB_REFRESH_ORPHAN_EBS = "refresh_orphan_ebs"

    JOB_TYPE_CHOICES = [
        (JOB_REFRESH_FINANCIAL_REPORT, "Refresh Financial Report"),
        (JOB_REFRESH_ORPHAN_EBS, "Refresh Orphan EBS"),
    ]

    STATUS_PENDING = "PENDING"
    STATUS_QUEUED = "QUEUED"
    STATUS_RUNNING = "RUNNING"
    STATUS_SUCCEEDED = "SUCCEEDED"
    STATUS_FAILED = "FAILED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_QUEUED, "Queued"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCEEDED, "Succeeded"),
        (STATUS_FAILED, "Failed"),
    ]

    job_key = models.CharField(max_length=255, unique=True)
    job_type = models.CharField(max_length=50, choices=JOB_TYPE_CHOICES, db_index=True)

    tenant_id = models.CharField(max_length=100, db_index=True)
    company_id = models.CharField(max_length=100, blank=True, default="", db_index=True)
    scope_type = models.CharField(max_length=20, blank=True, default="", db_index=True)
    scope_id = models.CharField(max_length=100, blank=True, default="", db_index=True)
    project_id = models.CharField(max_length=100, blank=True, default="", db_index=True)

    period_year = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    period_month = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    snapshot_date = models.DateField(null=True, blank=True, db_index=True)

    priority = models.PositiveIntegerField(default=5)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)

    payload = models.JSONField(default=dict)
    payload_hash = models.CharField(max_length=128, blank=True, default="")

    requested_at = models.DateTimeField(default=timezone.now)
    queued_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    broker_message_id = models.CharField(max_length=255, blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheduled_job_execution"
        indexes = [
            models.Index(fields=["job_type", "status"], name="idx_job_type_status"),
            models.Index(fields=["tenant_id", "job_type"], name="idx_job_tenant_type"),
        ]

    def __str__(self) -> str:
        return f"{self.job_type}:{self.job_key}:{self.status}"


class SchedulerLock(models.Model):
    name = models.CharField(max_length=100, unique=True)
    locked_until = models.DateTimeField()
    locked_by = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheduler_lock"

    def __str__(self) -> str:
        return f"{self.name}:{self.locked_by}"