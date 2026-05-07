from django.conf import settings
from django.db import models


class CompanyAccess(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_access",
    )
    tenant_id = models.CharField(max_length=100, db_index=True)
    company_id = models.CharField(max_length=100, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "company_access"
        indexes = [
            models.Index(fields=["tenant_id", "company_id"], name="idx_company_access_scope"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username}:{self.tenant_id}:{self.company_id}"
