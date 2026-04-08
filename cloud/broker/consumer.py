import json
import logging

import pika
from django.conf import settings

from cloud.logic.job_handlers import (
    PermanentJobError,
    TransientJobError,
    handle_financial_report_job,
    handle_orphan_ebs_job,
)
from jobs.broker.connection import build_connection_parameters
from jobs.broker.constants import (
    FINANCIAL_REFRESH_QUEUE,
    ORPHAN_EBS_REFRESH_QUEUE,
)
from jobs.logic.job_registry_logic import (
    get_job_by_key,
    mark_job_failed,
    mark_job_running,
    mark_job_succeeded,
)
from jobs.models import ScheduledJobExecution

logger = logging.getLogger(__name__)


def _dispatch_payload(payload: dict) -> None:
    job_type = payload["job_type"]
    region = settings.AWS_CLOUD_CONFIG["REGION"]

    if job_type == ScheduledJobExecution.JOB_REFRESH_FINANCIAL_REPORT:
        handle_financial_report_job(payload)
        return

    if job_type == ScheduledJobExecution.JOB_REFRESH_ORPHAN_EBS:
        handle_orphan_ebs_job(payload, region=region)
        return

    raise PermanentJobError(f"Tipo de job no soportado: {job_type}")


class CloudJobConsumer:
    def __init__(self) -> None:
        self.connection = None
        self.channel = None

    def connect(self) -> None:
        parameters = build_connection_parameters()
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)

    def consume_forever(self) -> None:
        if not self.channel:
            raise RuntimeError("El consumer no está conectado.")

        self.channel.basic_consume(
            queue=FINANCIAL_REFRESH_QUEUE,
            on_message_callback=self._on_message,
            auto_ack=False,
        )
        self.channel.basic_consume(
            queue=ORPHAN_EBS_REFRESH_QUEUE,
            on_message_callback=self._on_message,
            auto_ack=False,
        )

        logger.info("Cloud consumer started. Waiting for messages.")
        self.channel.start_consuming()

    def close(self) -> None:
        if self.connection and self.connection.is_open:
            self.connection.close()

    def _on_message(self, channel, method, properties, body) -> None:
        job = None
        try:
            payload = json.loads(body.decode("utf-8"))
            job_key = payload["job_key"]

            job = get_job_by_key(job_key)
            mark_job_running(job)

            _dispatch_payload(payload)

            mark_job_succeeded(job)
            channel.basic_ack(delivery_tag=method.delivery_tag)

        except PermanentJobError as exc:
            logger.exception("Permanent job error.")
            if job:
                mark_job_failed(job, str(exc))
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

        except TransientJobError as exc:
            logger.exception("Transient job error.")
            if job:
                mark_job_failed(job, str(exc))
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        except Exception as exc:
            logger.exception("Unexpected cloud consumer error.")
            if job:
                mark_job_failed(job, str(exc))
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)