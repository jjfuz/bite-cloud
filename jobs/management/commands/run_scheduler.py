from django.core.management.base import BaseCommand

from jobs.logic.scheduler_logic import run_scheduler_cycle


class Command(BaseCommand):
    help = "Ejecuta un ciclo de scheduling para refrescar snapshots y publicar jobs."

    def handle(self, *args, **options):
        run_scheduler_cycle()
        self.stdout.write(self.style.SUCCESS("Scheduler cycle completed successfully."))