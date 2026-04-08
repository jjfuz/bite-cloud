from django.db import models


class FinancialReportSnapshot(models.Model):
    SCOPE_CLIENT = "client"
    SCOPE_AREA = "area"
    SCOPE_PROJECT = "project"

    SCOPE_CHOICES = [
        (SCOPE_CLIENT, "Client"),
        (SCOPE_AREA, "Area"),
        (SCOPE_PROJECT, "Project"),
    ]

    REPORT_TYPE_MONTHLY = "financial_monthly"
    REPORT_TYPE_CHOICES = [
        (REPORT_TYPE_MONTHLY, "Financial Monthly"),
    ]

    tenant_id = models.CharField(max_length=100, db_index=True)
    company_id = models.CharField(max_length=100, db_index=True)
    scope_type = models.CharField(max_length=20, choices=SCOPE_CHOICES, db_index=True)
    scope_id = models.CharField(max_length=100, db_index=True)

    period_year = models.PositiveIntegerField(db_index=True)
    period_month = models.PositiveIntegerField(db_index=True)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPE_CHOICES, db_index=True)

    currency = models.CharField(max_length=10, default="USD")
    total_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    report_payload = models.JSONField(default=dict)

    source_version = models.CharField(max_length=100, blank=True, default="")
    generated_at = models.DateTimeField()
    is_current = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "financial_report_snapshot"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "tenant_id",
                    "scope_type",
                    "scope_id",
                    "period_year",
                    "period_month",
                    "report_type",
                    "is_current",
                ],
                name="uq_current_financial_snapshot",
            )
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "scope_type", "scope_id", "period_year", "period_month"],
                name="idx_financial_lookup",
            ),
            models.Index(
                fields=["tenant_id", "company_id", "period_year", "period_month"],
                name="idx_financial_company_period",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.report_type}:{self.tenant_id}:{self.scope_type}:"
            f"{self.scope_id}:{self.period_year}-{self.period_month:02d}"
        )


class OrphanEBSSnapshot(models.Model):
    tenant_id = models.CharField(max_length=100, db_index=True)
    company_id = models.CharField(max_length=100, db_index=True)
    project_id = models.CharField(max_length=100, db_index=True)

    snapshot_date = models.DateField(db_index=True)

    volume_id = models.CharField(max_length=100, db_index=True)
    volume_name = models.CharField(max_length=255, blank=True, default="")
    region = models.CharField(max_length=50, db_index=True)

    volume_type = models.CharField(max_length=50, blank=True, default="")
    size_gib = models.PositiveIntegerField(default=0)
    monthly_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="USD")

    ranking_position = models.PositiveIntegerField(default=0, db_index=True)
    details_payload = models.JSONField(default=dict)

    generated_at = models.DateTimeField()

    class Meta:
        db_table = "orphan_ebs_snapshot"
        indexes = [
            models.Index(
                fields=["tenant_id", "company_id", "project_id", "snapshot_date"],
                name="idx_orphan_snapshot_lookup",
            ),
            models.Index(
                fields=["tenant_id", "project_id", "monthly_cost"],
                name="idx_orphan_project_cost",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.volume_id}:{self.project_id}:{self.snapshot_date}"