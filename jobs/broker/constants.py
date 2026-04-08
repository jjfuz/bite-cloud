FINANCIAL_REFRESH_ROUTING_KEY = "cloud.refresh.financial"
ORPHAN_EBS_REFRESH_ROUTING_KEY = "cloud.refresh.orphan_ebs"

FINANCIAL_REFRESH_QUEUE = "q.cloud.refresh.financial"
ORPHAN_EBS_REFRESH_QUEUE = "q.cloud.refresh.orphan_ebs"

FINANCIAL_REFRESH_DLQ = "q.cloud.refresh.financial.dlq"
ORPHAN_EBS_REFRESH_DLQ = "q.cloud.refresh.orphan_ebs.dlq"

MAX_PRIORITY = 10
PERSISTENT_DELIVERY_MODE = 2
CONTENT_TYPE_JSON = "application/json"

JOB_TYPE_TO_ROUTING_KEY = {
    "refresh_financial_report": FINANCIAL_REFRESH_ROUTING_KEY,
    "refresh_orphan_ebs": ORPHAN_EBS_REFRESH_ROUTING_KEY,
}