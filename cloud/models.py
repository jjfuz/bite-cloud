from django.db import models


class RawCostRecord(models.Model):
    tenant_id = models.CharField(max_length=100, db_index=True)
    company_id = models.CharField(max_length=100, db_index=True)
    area_id = models.CharField(max_length=100, blank=True, default="", db_index=True)
    project_id = models.CharField(max_length=100, db_index=True)

    service_name = models.CharField(max_length=100, db_index=True)
    period_year = models.PositiveIntegerField(db_index=True)
    period_month = models.PositiveIntegerField(db_index=True)

    currency = models.CharField(max_length=10, default="USD")
    cost_amount = models.DecimalField(max_digits=14, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "raw_cost_record"
        indexes = [
            models.Index(
                fields=["tenant_id", "company_id", "period_year", "period_month"],
                name="idx_raw_cost_company_period",
            ),
            models.Index(
                fields=["tenant_id", "project_id", "period_year", "period_month"],
                name="idx_raw_cost_project_period",
            ),
            models.Index(
                fields=["tenant_id", "area_id", "period_year", "period_month"],
                name="idx_raw_cost_area_period",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.tenant_id}:{self.company_id}:{self.project_id}:"
            f"{self.service_name}:{self.period_year}-{self.period_month:02d}"
        )