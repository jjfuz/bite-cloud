import boto3
from django.conf import settings


def build_boto3_session():
    config = settings.AWS_CLOUD_CONFIG

    if config["USE_IAM_ROLE"]:
        return boto3.Session(region_name=config["REGION"])

    return boto3.Session(
        aws_access_key_id=config["ACCESS_KEY_ID"],
        aws_secret_access_key=config["SECRET_ACCESS_KEY"],
        aws_session_token=config["SESSION_TOKEN"] or None,
        region_name=config["REGION"],
    )


def build_ec2_client():
    session = build_boto3_session()
    return session.client("ec2", region_name=settings.AWS_CLOUD_CONFIG["REGION"])


def build_cost_explorer_client():
    session = build_boto3_session()
    return session.client("ce", region_name=settings.AWS_CLOUD_CONFIG["CE_REGION"])