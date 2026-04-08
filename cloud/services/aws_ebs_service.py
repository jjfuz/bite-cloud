from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from cloud.services.aws_session_service import build_ec2_client
from cloud.services.pricing_policy_service import estimate_ebs_monthly_cost


@dataclass(frozen=True)
class OrphanEBSRecord:
    volume_id: str
    volume_name: str
    region: str
    volume_type: str
    size_gib: int
    monthly_cost: Decimal
    project_id: str
    raw_payload: dict


def _extract_tag_value(tags: list[dict], target_key: str) -> str:
    for tag in tags or []:
        if tag.get("Key") == target_key:
            return tag.get("Value", "")
    return ""


def list_orphan_ebs_for_project(project_id: str, region: str) -> list[OrphanEBSRecord]:
    ec2_client = build_ec2_client()

    paginator = ec2_client.get_paginator("describe_volumes")
    pages = paginator.paginate(
        Filters=[
            {"Name": "status", "Values": ["available"]},
        ]
    )

    records: list[OrphanEBSRecord] = []

    for page in pages:
        for volume in page.get("Volumes", []):
            tags = volume.get("Tags", [])
            volume_project_id = (
                _extract_tag_value(tags, "ProjectId")
                or _extract_tag_value(tags, "project_id")
                or _extract_tag_value(tags, "Project")
            )

            if volume_project_id != project_id:
                continue

            volume_type = volume.get("VolumeType", "gp3")
            size_gib = int(volume.get("Size", 0))
            monthly_cost = estimate_ebs_monthly_cost(size_gib=size_gib, volume_type=volume_type)

            record = OrphanEBSRecord(
                volume_id=volume["VolumeId"],
                volume_name=_extract_tag_value(tags, "Name"),
                region=region,
                volume_type=volume_type,
                size_gib=size_gib,
                monthly_cost=monthly_cost,
                project_id=project_id,
                raw_payload=volume,
            )
            records.append(record)

    records.sort(key=lambda item: (-item.monthly_cost, item.volume_id))
    return records