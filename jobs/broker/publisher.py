import json
import logging
from typing import Optional

import pika
from django.conf import settings

from jobs.broker.connection import get_blocking_connection
from jobs.broker.constants import (
    CONTENT_TYPE_JSON,
    JOB_TYPE_TO_ROUTING_KEY,
    PERSISTENT_DELIVERY_MODE,
)
from jobs.broker.topology import declare_broker_topology

logger = logging.getLogger(__name__)


class BrokerPublisherError(Exception):
    """Se lanza cuando falla la publicación de un mensaje al broker."""


def resolve_routing_key(job_type: str) -> str:
    try:
        return JOB_TYPE_TO_ROUTING_KEY[job_type]
    except KeyError as exc:
        raise BrokerPublisherError(
            f"No existe routing key configurada para el job_type '{job_type}'."
        ) from exc


def build_basic_properties(priority: int) -> pika.BasicProperties:
    return pika.BasicProperties(
        delivery_mode=PERSISTENT_DELIVERY_MODE,
        content_type=CONTENT_TYPE_JSON,
        priority=priority,
    )


def publish_job(payload: dict) -> Optional[str]:
    if settings.USE_FAKE_BROKER:
        return f"fake-msg-{payload['job_key']}"
    if "job_type" not in payload:
        raise BrokerPublisherError("El payload no contiene el campo obligatorio 'job_type'.")

    if "job_key" not in payload:
        raise BrokerPublisherError("El payload no contiene el campo obligatorio 'job_key'.")

    routing_key = resolve_routing_key(payload["job_type"])
    priority = int(payload.get("priority", 5))
    exchange_name = settings.RABBITMQ_CONFIG["EXCHANGE"]

    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    properties = build_basic_properties(priority=priority)

    try:
        with get_blocking_connection() as connection:
            channel = connection.channel()

            declare_broker_topology(channel)

            channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,
                body=body,
                properties=properties,
                mandatory=True,
            )

            logger.info(
                "Published message to RabbitMQ exchange=%s routing_key=%s job_key=%s",
                exchange_name,
                routing_key,
                payload["job_key"],
            )

            return payload["job_key"]

    except Exception as exc:
        logger.exception(
            "Failed to publish message to RabbitMQ. job_key=%s",
            payload.get("job_key"),
        )
        raise BrokerPublisherError(
            f"No fue posible publicar el job '{payload.get('job_key')}' al broker."
        ) from exc