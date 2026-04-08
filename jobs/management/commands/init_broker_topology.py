from django.core.management.base import BaseCommand

from jobs.broker.connection import get_blocking_connection
from jobs.broker.topology import declare_broker_topology


class Command(BaseCommand):
    help = "Declara la topología necesaria en RabbitMQ."

    def handle(self, *args, **options):
        with get_blocking_connection() as connection:
            channel = connection.channel()
            declare_broker_topology(channel)

        self.stdout.write(self.style.SUCCESS("RabbitMQ topology initialized successfully."))