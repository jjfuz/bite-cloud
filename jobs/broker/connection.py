import logging
from contextlib import contextmanager

import pika
from django.conf import settings

logger = logging.getLogger(__name__)


class RabbitMQConnectionError(Exception):
    """Se lanza cuando no es posible abrir una conexión con RabbitMQ."""


def build_connection_parameters() -> pika.ConnectionParameters:
    config = settings.RABBITMQ_CONFIG

    credentials = pika.PlainCredentials(
        username=config["USERNAME"],
        password=config["PASSWORD"],
    )

    return pika.ConnectionParameters(
        host=config["HOST"],
        port=config["PORT"],
        virtual_host=config["VHOST"],
        credentials=credentials,
        heartbeat=config["HEARTBEAT"],
        blocked_connection_timeout=config["BLOCKED_CONNECTION_TIMEOUT"],
        connection_attempts=config["CONNECTION_ATTEMPTS"],
        retry_delay=config["RETRY_DELAY"],
        socket_timeout=config["SOCKET_TIMEOUT"],
    )


@contextmanager
def get_blocking_connection():
    connection = None
    try:
        parameters = build_connection_parameters()
        connection = pika.BlockingConnection(parameters)
        yield connection
    except pika.exceptions.AMQPError as exc:
        logger.exception("RabbitMQ AMQP error while opening connection.")
        raise RabbitMQConnectionError(
            "No fue posible establecer conexión con RabbitMQ."
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected RabbitMQ connection error.")
        raise RabbitMQConnectionError(
            "Ocurrió un error inesperado al conectar con RabbitMQ."
        ) from exc
    finally:
        if connection and connection.is_open:
            connection.close()