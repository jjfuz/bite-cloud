import random
from decimal import Decimal

from django.core.management.base import BaseCommand

from cloud.models import RawCostRecord


class Command(BaseCommand):
    help = "Puebla la tabla RawCostRecord con datos sintéticos para ASR 2."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", type=str, default="tenant-demo")
        parser.add_argument("--companies", type=int, default=200)
        parser.add_argument("--areas-per-company", type=int, default=3)
        parser.add_argument("--projects-per-company", type=int, default=5)
        parser.add_argument("--year", type=int, default=2026)
        parser.add_argument("--clear", action="store_true")

    def handle(self, *args, **options):
        tenant_id = options["tenant_id"]
        companies = options["companies"]
        areas_per_company = options["areas_per_company"]
        projects_per_company = options["projects_per_company"]
        year = options["year"]
        clear = options["clear"]

        services = ["EC2", "RDS", "S3", "EKS", "Lambda", "CloudFront", "DynamoDB"]

        if clear:
            RawCostRecord.objects.filter(tenant_id=tenant_id).delete()
            self.stdout.write(self.style.WARNING(f"Datos previos eliminados para tenant={tenant_id}"))

        batch = []
        batch_size = 5000
        total_inserted = 0

        for company_number in range(1, companies + 1):
            company_id = f"company-{company_number:03d}"

            for project_number in range(1, projects_per_company + 1):
                project_id = f"{company_id}-project-{project_number:03d}"
                area_number = ((project_number - 1) % areas_per_company) + 1
                area_id = f"{company_id}-area-{area_number:03d}"

                for month in range(1, 13):
                    for service_name in services:
                        cost_amount = Decimal(str(round(random.uniform(5.0, 2500.0), 2)))

                        batch.append(
                            RawCostRecord(
                                tenant_id=tenant_id,
                                company_id=company_id,
                                area_id=area_id,
                                project_id=project_id,
                                service_name=service_name,
                                period_year=year,
                                period_month=month,
                                currency="USD",
                                cost_amount=cost_amount,
                            )
                        )

                        if len(batch) >= batch_size:
                            RawCostRecord.objects.bulk_create(batch, batch_size=batch_size)
                            total_inserted += len(batch)
                            batch = []

        if batch:
            RawCostRecord.objects.bulk_create(batch, batch_size=batch_size)
            total_inserted += len(batch)

        self.stdout.write(self.style.SUCCESS(f"Insertados {total_inserted} registros en RawCostRecord."))