from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import boto3
from django.conf import settings
from moto import mock_aws


@dataclass(frozen=True)
class OrphanEBSRecord:
    volume_id: str
    volume_name: str
    region: str
    volume_type: str
    size_gib: int
    monthly_cost: Decimal
    project_id: str
    raw_payload: dict[str, Any]


def _get_rate(volume_type: str) -> Decimal:
    rates = settings.CLOUD_EXPERIMENT_CONFIG["EBS_MONTHLY_RATES"]
    rate = rates.get(volume_type, rates["gp3"])
    return Decimal(str(rate))


def _estimate_monthly_cost(size_gib: int, volume_type: str) -> Decimal:
    return Decimal(size_gib) * _get_rate(volume_type)


def _extract_tag_value(tags: list[dict], target_key: str) -> str:
    for tag in tags or []:
        if tag.get("Key") == target_key:
            return tag.get("Value", "")
    return ""


def _build_create_volume_kwargs(
    project_id: str,
    size_gib: int,
    volume_type: str,
    name: str,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "AvailabilityZone": "us-east-1a",
        "Size": size_gib,
        "VolumeType": volume_type,
        "TagSpecifications": [
            {
                "ResourceType": "volume",
                "Tags": [
                    {"Key": "ProjectId", "Value": project_id},
                    {"Key": "Name", "Value": name},
                ],
            }
        ],
    }

    if volume_type in {"io1", "io2"}:
        kwargs["Iops"] = max(100, size_gib * 50)

    return kwargs


def _create_orphan_volume(
    ec2_client,
    project_id: str,
    size_gib: int,
    volume_type: str,
    index: int,
) -> None:
    kwargs = _build_create_volume_kwargs(
        project_id=project_id,
        size_gib=size_gib,
        volume_type=volume_type,
        name=f"orphan-{index}",
    )
    ec2_client.create_volume(**kwargs)


def _create_noise_orphan_volume(
    ec2_client,
    project_id: str,
    size_gib: int,
    volume_type: str,
    index: int,
) -> None:
    kwargs = _build_create_volume_kwargs(
        project_id=f"other-{project_id}",
        size_gib=size_gib,
        volume_type=volume_type,
        name=f"noise-orphan-{index}",
    )
    ec2_client.create_volume(**kwargs)


def _create_attached_volume(
    ec2_client,
    instance_id: str,
    project_id: str,
    size_gib: int,
    volume_type: str,
    index: int,
) -> None:
    kwargs = _build_create_volume_kwargs(
        project_id=project_id,
        size_gib=size_gib,
        volume_type=volume_type,
        name=f"attached-{index}",
    )

    response = ec2_client.create_volume(**kwargs)
    volume_id = response["VolumeId"]

    ec2_client.attach_volume(
        Device=f"/dev/sd{chr(102 + (index % 10))}",
        InstanceId=instance_id,
        VolumeId=volume_id,
    )


def _seed_moto_infrastructure(ec2_client, project_id: str) -> None:
    config = settings.CLOUD_EXPERIMENT_CONFIG

    orphan_count = config["MOTO_EBS_ORPHAN_COUNT"]
    noise_count = config["MOTO_EBS_NOISE_COUNT"]
    instance_count = config["MOTO_EBS_INSTANCE_COUNT"]

    sizes = [8, 50, 100, 500, 1000]
    volume_types = ["gp2", "gp3", "io1"]

    instances = ec2_client.run_instances(
        ImageId="ami-12345678",
        MinCount=instance_count,
        MaxCount=instance_count,
        InstanceType="t2.micro",
    )["Instances"]

    target_instance_id = instances[0]["InstanceId"]

    for i in range(orphan_count):
        _create_orphan_volume(
            ec2_client=ec2_client,
            project_id=project_id,
            size_gib=sizes[i % len(sizes)],
            volume_type=volume_types[i % len(volume_types)],
            index=i,
        )

    for i in range(noise_count):
        _create_noise_orphan_volume(
            ec2_client=ec2_client,
            project_id=project_id,
            size_gib=sizes[i % len(sizes)],
            volume_type=volume_types[i % len(volume_types)],
            index=i,
        )

    for i in range(min(20, orphan_count)):
        _create_attached_volume(
            ec2_client=ec2_client,
            instance_id=target_instance_id,
            project_id=project_id,
            size_gib=sizes[i % len(sizes)],
            volume_type=volume_types[i % len(volume_types)],
            index=i,
        )


def _extract_orphan_ebs_for_project(
    ec2_client,
    project_id: str,
    region: str,
) -> list[OrphanEBSRecord]:
    response = ec2_client.describe_volumes(
        Filters=[{"Name": "status", "Values": ["available"]}]
    )

    records: list[OrphanEBSRecord] = []

    for volume in response.get("Volumes", []):
        tags = volume.get("Tags", [])
        volume_project_id = _extract_tag_value(tags, "ProjectId")

        if volume_project_id != project_id:
            continue

        volume_type = volume.get("VolumeType", "gp3")
        size_gib = int(volume.get("Size", 0))
        monthly_cost = _estimate_monthly_cost(
            size_gib=size_gib,
            volume_type=volume_type,
        )

        records.append(
            OrphanEBSRecord(
                volume_id=volume["VolumeId"],
                volume_name=_extract_tag_value(tags, "Name"),
                region=region,
                volume_type=volume_type,
                size_gib=size_gib,
                monthly_cost=monthly_cost,
                project_id=project_id,
                raw_payload=volume,
            )
        )

    records.sort(key=lambda item: (-item.monthly_cost, item.volume_id))
    return records


def build_orphan_ebs_snapshot_from_moto(
    project_id: str,
    region: str,
) -> list[OrphanEBSRecord]:
    with mock_aws():
        ec2_client = boto3.client("ec2", region_name=region)
        _seed_moto_infrastructure(
            ec2_client=ec2_client,
            project_id=project_id,
        )
        return _extract_orphan_ebs_for_project(
            ec2_client=ec2_client,
            project_id=project_id,
            region=region,
        )