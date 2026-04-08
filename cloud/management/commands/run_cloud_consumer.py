import logging

from django.core.management.base import BaseCommand

from cloud.broker.consumer import CloudJobConsumer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ejecuta el consumer del manejador cloud para jobs RabbitMQ."

    def handle(self, *args, **options):
        consumer = CloudJobConsumer()

        try:
            consumer.connect()
            consumer.consume_forever()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Cloud consumer interrupted by user."))
        finally:
            consumer.close()
            self.stdout.write(self.style.SUCCESS("Cloud consumer stopped."))