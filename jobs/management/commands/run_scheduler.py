from django.core.management.base import BaseCommand

from jobs.logic.scheduler_logic import run_scheduler_cycle


class Command(BaseCommand):
    help = "Ejecuta un ciclo de scheduling para refrescar snapshots y publicar jobs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--locked-by",
            type=str,
            default="scheduler-node",
            help="Identificador lógico del nodo que ejecuta el scheduler.",
        )

    def handle(self, *args, **options):
        locked_by = options["locked_by"]
        run_scheduler_cycle(locked_by=locked_by)
        self.stdout.write(self.style.SUCCESS("Scheduler cycle completed successfully."))