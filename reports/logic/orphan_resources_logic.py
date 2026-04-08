from typing import Any

from reports.models import OrphanEBSSnapshot


def get_orphan_ebs_snapshot(
    tenant_id: str,
    company_id: str,
    project_id: str,
    snapshot_date,
) -> list[OrphanEBSSnapshot]:
    queryset = (
        OrphanEBSSnapshot.objects.filter(
            tenant_id=tenant_id,
            company_id=company_id,
            project_id=project_id,
            snapshot_date=snapshot_date,
        )
        .order_by("-monthly_cost", "volume_id")
    )
    return list(queryset)


def serialize_orphan_ebs_snapshot(records: list[OrphanEBSSnapshot]) -> dict[str, Any]:
    if not records:
        return {
            "snapshot_date": None,
            "total_orphan_volumes": 0,
            "items": [],
        }

    return {
        "snapshot_date": records[0].snapshot_date.isoformat(),
        "total_orphan_volumes": len(records),
        "items": [
            {
                "volume_id": record.volume_id,
                "volume_name": record.volume_name,
                "region": record.region,
                "volume_type": record.volume_type,
                "size_gib": record.size_gib,
                "monthly_cost": str(record.monthly_cost),
                "currency": record.currency,
                "ranking_position": record.ranking_position,
                "details": record.details_payload,
            }
            for record in records
        ],
    }