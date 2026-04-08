from django.core.management.base import BaseCommand

from jobs.broker.connection import get_blocking_connection


class Command(BaseCommand):
    help = "Verifica conectividad básica con RabbitMQ."

    def handle(self, *args, **options):
        with get_blocking_connection() as connection:
            channel = connection.channel()
            channel.queue_declare(queue="", exclusive=True)

        self.stdout.write(self.style.SUCCESS("RabbitMQ healthcheck OK."))