from decimal import Decimal

from django.conf import settings


def get_monthly_rate_per_gib(volume_type: str) -> Decimal:
    rates = settings.AWS_CLOUD_CONFIG["EBS_MONTHLY_RATES"]
    normalized_volume_type = (volume_type or "gp3").lower()
    rate = rates.get(normalized_volume_type, rates["gp3"])
    return Decimal(str(rate))


def estimate_ebs_monthly_cost(size_gib: int, volume_type: str) -> Decimal:
    rate = get_monthly_rate_per_gib(volume_type)
    return rate * Decimal(size_gib)