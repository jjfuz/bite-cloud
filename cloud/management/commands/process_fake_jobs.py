from django.conf import settings
from django.core.management.base import BaseCommand

from cloud.logic.fake_job_handlers import (
    handle_fake_financial_report_job,
    handle_fake_orphan_ebs_job,
)
from cloud.logic.job_handlers import (
    handle_financial_report_job,
    handle_orphan_ebs_job,
)
from jobs.logic.job_registry_logic import (
    mark_job_failed,
    mark_job_running,
    mark_job_succeeded,
)
from jobs.models import ScheduledJobExecution


class Command(BaseCommand):
    help = "Procesa jobs QUEUED desde BD sin usar RabbitMQ."

    def handle(self, *args, **options):
        queued_jobs = ScheduledJobExecution.objects.filter(
            status=ScheduledJobExecution.STATUS_QUEUED
        ).order_by("requested_at")

        processed_count = 0

        for job in queued_jobs:
            try:
                mark_job_running(job)

                payload = job.payload
                region = settings.AWS_CLOUD_CONFIG["REGION"]

                if payload["job_type"] == ScheduledJobExecution.JOB_REFRESH_FINANCIAL_REPORT:
                    if settings.USE_FAKE_CLOUD_DATA:
                        handle_fake_financial_report_job(payload)
                    else:
                        handle_financial_report_job(payload)

                elif payload["job_type"] == ScheduledJobExecution.JOB_REFRESH_ORPHAN_EBS:
                    if settings.USE_FAKE_CLOUD_DATA:
                        handle_fake_orphan_ebs_job(payload, region=region)
                    else:
                        handle_orphan_ebs_job(payload, region=region)

                else:
                    raise ValueError(f"Tipo de job no soportado: {payload['job_type']}")

                mark_job_succeeded(job)
                processed_count += 1

            except Exception as exc:
                mark_job_failed(job, str(exc))

        self.stdout.write(
            self.style.SUCCESS(f"Procesamiento fake finalizado. Jobs procesados: {processed_count}")
        )