from django.core.management.base import BaseCommand

from cloud.models import RawCostRecord
from jobs.models import ScheduledJobExecution
from reports.models import FinancialReportSnapshot, OrphanEBSSnapshot


class Command(BaseCommand):
    help = "Limpia datos del experimento local."

    def add_arguments(self, parser):
        parser.add_argument("--delete-raw-costs", action="store_true")

    def handle(self, *args, **options):
        OrphanEBSSnapshot.objects.all().delete()
        FinancialReportSnapshot.objects.all().delete()
        ScheduledJobExecution.objects.all().delete()

        if options["delete_raw_costs"]:
            RawCostRecord.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("Datos del experimento local limpiados correctamente."))