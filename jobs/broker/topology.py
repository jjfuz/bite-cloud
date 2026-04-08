import logging

from django.conf import settings

from jobs.broker.constants import (
    FINANCIAL_REFRESH_DLQ,
    FINANCIAL_REFRESH_QUEUE,
    FINANCIAL_REFRESH_ROUTING_KEY,
    MAX_PRIORITY,
    ORPHAN_EBS_REFRESH_DLQ,
    ORPHAN_EBS_REFRESH_QUEUE,
    ORPHAN_EBS_REFRESH_ROUTING_KEY,
)

logger = logging.getLogger(__name__)


def declare_broker_topology(channel) -> None:
    config = settings.RABBITMQ_CONFIG
    exchange_name = config["EXCHANGE"]
    exchange_type = config["EXCHANGE_TYPE"]
    dlx_name = config["DLX"]

    channel.exchange_declare(
        exchange=exchange_name,
        exchange_type=exchange_type,
        durable=True,
    )

    channel.exchange_declare(
        exchange=dlx_name,
        exchange_type="topic",
        durable=True,
    )

    channel.queue_declare(
        queue=FINANCIAL_REFRESH_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": dlx_name,
            "x-max-priority": MAX_PRIORITY,
        },
    )
    channel.queue_bind(
        exchange=exchange_name,
        queue=FINANCIAL_REFRESH_QUEUE,
        routing_key=FINANCIAL_REFRESH_ROUTING_KEY,
    )

    channel.queue_declare(
        queue=ORPHAN_EBS_REFRESH_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": dlx_name,
            "x-max-priority": MAX_PRIORITY,
        },
    )
    channel.queue_bind(
        exchange=exchange_name,
        queue=ORPHAN_EBS_REFRESH_QUEUE,
        routing_key=ORPHAN_EBS_REFRESH_ROUTING_KEY,
    )

    channel.queue_declare(
        queue=FINANCIAL_REFRESH_DLQ,
        durable=True,
    )
    channel.queue_bind(
        exchange=dlx_name,
        queue=FINANCIAL_REFRESH_DLQ,
        routing_key=FINANCIAL_REFRESH_ROUTING_KEY,
    )

    channel.queue_declare(
        queue=ORPHAN_EBS_REFRESH_DLQ,
        durable=True,
    )
    channel.queue_bind(
        exchange=dlx_name,
        queue=ORPHAN_EBS_REFRESH_DLQ,
        routing_key=ORPHAN_EBS_REFRESH_ROUTING_KEY,
    )

    logger.info("RabbitMQ topology declared successfully.")