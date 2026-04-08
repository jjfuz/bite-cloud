from dateutil.parser import isoparse
from django.conf import settings

from cloud.logic.snapshot_writer_logic import (
    replace_financial_report_snapshot,
    replace_orphan_ebs_snapshot,
)
from cloud.services.internal_cost_service import (
    build_monthly_financial_report_from_internal_data,
)
from cloud.services.moto_ebs_service import (
    build_orphan_ebs_snapshot_from_moto,
)


class PermanentJobError(Exception):
    pass


class TransientJobError(Exception):
    pass


def handle_financial_report_job(payload: dict) -> None:
    try:
        tenant_id = payload["tenant_id"]
        company_id = payload["company_id"]
        scope_type = payload["scope_type"]
        scope_id = payload["scope_id"]
        period_year = int(payload["period_year"])
        period_month = int(payload["period_month"])
    except KeyError as exc:
        raise PermanentJobError(f"Payload financiero inválido. Falta el campo {exc}.") from exc

    source_mode = settings.CLOUD_EXPERIMENT_CONFIG["FINANCIAL_REPORT_SOURCE"]

    if source_mode != "internal_db":
        raise PermanentJobError(
            f"Modo financiero no soportado para este experimento: {source_mode}"
        )

    try:
        result = build_monthly_financial_report_from_internal_data(
            tenant_id=tenant_id,
            company_id=company_id,
            scope_type=scope_type,
            scope_id=scope_id,
            period_year=period_year,
            period_month=period_month,
        )

        replace_financial_report_snapshot(
            tenant_id=tenant_id,
            company_id=company_id,
            scope_type=scope_type,
            scope_id=scope_id,
            period_year=period_year,
            period_month=period_month,
            result=result,
        )
    except Exception as exc:
        raise TransientJobError("Falló la generación del snapshot financiero.") from exc


def handle_orphan_ebs_job(payload: dict) -> None:
    try:
        tenant_id = payload["tenant_id"]
        company_id = payload["company_id"]
        project_id = payload["project_id"]
        snapshot_date = isoparse(payload["snapshot_date"]).date()
    except KeyError as exc:
        raise PermanentJobError(f"Payload orphan EBS inválido. Falta el campo {exc}.") from exc

    source_mode = settings.CLOUD_EXPERIMENT_CONFIG["ORPHAN_EBS_SOURCE"]
    region = settings.CLOUD_EXPERIMENT_CONFIG["AWS_REGION"]

    if source_mode != "moto":
        raise PermanentJobError(
            f"Modo orphan EBS no soportado para este experimento: {source_mode}"
        )

    try:
        records = build_orphan_ebs_snapshot_from_moto(
            project_id=project_id,
            region=region,
        )

        replace_orphan_ebs_snapshot(
            tenant_id=tenant_id,
            company_id=company_id,
            project_id=project_id,
            snapshot_date=snapshot_date,
            region=region,
            records=records,
        )
    except Exception as exc:
        raise TransientJobError(
            f"Falló la generación del snapshot de volúmenes EBS huérfanos. "
            f"Causa original: {type(exc).__name__}: {exc}"
        ) from exc