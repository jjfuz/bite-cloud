from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from jobs.models import SchedulerLock


def acquire_scheduler_lock(lock_name: str, locked_by: str, lease_seconds: int = 120) -> bool:
    now = timezone.now()
    lock_until = now + timedelta(seconds=lease_seconds)

    with transaction.atomic():
        lock, created = SchedulerLock.objects.select_for_update().get_or_create(
            name=lock_name,
            defaults={
                "locked_until": lock_until,
                "locked_by": locked_by,
            },
        )

        if created:
            return True

        if lock.locked_until <= now:
            lock.locked_until = lock_until
            lock.locked_by = locked_by
            lock.save(update_fields=["locked_until", "locked_by", "updated_at"])
            return True

        return False


def release_scheduler_lock(lock_name: str, locked_by: str) -> None:
    with transaction.atomic():
        lock = SchedulerLock.objects.select_for_update().filter(
            name=lock_name,
            locked_by=locked_by,
        ).first()

        if lock:
            lock.locked_until = timezone.now()
            lock.save(update_fields=["locked_until", "updated_at"])