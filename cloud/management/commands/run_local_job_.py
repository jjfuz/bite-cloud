from datetime import date
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError

from cloud.logic.job_handlers import (
    handle_financial_report_job,
    handle_orphan_ebs_job,
)
from jobs.broker.payload_builders import (
    build_financial_report_refresh_payload,
    build_orphan_ebs_refresh_payload,
)
from jobs.logic.job_registry_logic import (
    create_pending_job,
    mark_job_failed,
    mark_job_running,
    mark_job_succeeded,
)
from reports.models import FinancialReportSnapshot, OrphanEBSSnapshot


class Command(BaseCommand):
    help = "Ejecuta localmente un job sin pasar por RabbitMQ."

    def add_arguments(self, parser):
        parser.add_argument(
            "--job-type",
            type=str,
            required=True,
            choices=["refresh_financial_report", "refresh_orphan_ebs"],
            help="Tipo de job a ejecutar localmente.",
        )

        parser.add_argument("--tenant-id", type=str, default="tenant-demo")
        parser.add_argument("--company-id", type=str, default="company-demo")

        parser.add_argument("--scope-type", type=str, default="project")
        parser.add_argument("--scope-id", type=str, default="project-001")

        parser.add_argument("--project-id", type=str, default="project-001")

        parser.add_argument("--year", type=int, default=2026)
        parser.add_argument("--month", type=int, default=4)

        parser.add_argument(
            "--snapshot-date",
            type=str,
            default=date.today().isoformat(),
            help="Fecha ISO YYYY-MM-DD para snapshot de orphan EBS.",
        )

        parser.add_argument(
            "--force-new-key",
            action="store_true",
            help="Genera un job_key único para repetir pruebas locales sin conflictos.",
        )

    def handle(self, *args, **options):
        job_type = options["job_type"]
        tenant_id = options["tenant_id"]
        company_id = options["company_id"]
        force_new_key = options["force_new_key"]

        if job_type == "refresh_financial_report":
            payload = build_financial_report_refresh_payload(
                tenant_id=tenant_id,
                company_id=company_id,
                scope_type=options["scope_type"],
                scope_id=options["scope_id"],
                period_year=options["year"],
                period_month=options["month"],
                priority=5,
            )

            if force_new_key:
                payload["job_key"] = f"{payload['job_key']}:{uuid4()}"

            job = create_pending_job(payload)

            try:
                mark_job_running(job)
                handle_financial_report_job(payload)
                mark_job_succeeded(job)

                snapshot = FinancialReportSnapshot.objects.filter(
                    tenant_id=tenant_id,
                    scope_type=options["scope_type"],
                    scope_id=options["scope_id"],
                    period_year=options["year"],
                    period_month=options["month"],
                    is_current=True,
                ).first()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Job financiero ejecutado correctamente. "
                        f"snapshot_id={snapshot.id if snapshot else 'N/A'} "
                        f"total_cost={snapshot.total_cost if snapshot else 'N/A'}"
                    )
                )

            except Exception as exc:
                mark_job_failed(job, str(exc))
                raise CommandError(f"Falló el job financiero: {exc}") from exc

            return

        if job_type == "refresh_orphan_ebs":
            payload = build_orphan_ebs_refresh_payload(
                tenant_id=tenant_id,
                company_id=company_id,
                project_id=options["project_id"],
                snapshot_date=date.fromisoformat(options["snapshot_date"]),
                priority=3,
            )

            if force_new_key:
                payload["job_key"] = f"{payload['job_key']}:{uuid4()}"

            job = create_pending_job(payload)

            try:
                mark_job_running(job)
                handle_orphan_ebs_job(payload)
                mark_job_succeeded(job)

                count = OrphanEBSSnapshot.objects.filter(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    project_id=options["project_id"],
                    snapshot_date=date.fromisoformat(options["snapshot_date"]),
                ).count()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Job orphan EBS ejecutado correctamente. "
                        f"registros_generados={count}"
                    )
                )

            except Exception as exc:
                mark_job_failed(job, str(exc))
                raise CommandError(f"Falló el job orphan EBS: {exc}") from exc

            return