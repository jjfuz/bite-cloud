from dataclasses import dataclass

from django.core.exceptions import PermissionDenied

from common.models import CompanyAccess


@dataclass(frozen=True)
class RequestScope:
    tenant_id: str
    company_id: str


def get_request_scope(request) -> RequestScope:
    if hasattr(request, "company_scope"):
        return request.company_scope

    user = request.user
    if not user.is_authenticated:
        raise PermissionDenied("Authentication required")

    try:
        access = CompanyAccess.objects.only("tenant_id", "company_id").get(user=user)
    except CompanyAccess.DoesNotExist as exc:
        raise PermissionDenied("No company access configured for this user") from exc

    scope = RequestScope(tenant_id=access.tenant_id, company_id=access.company_id)
    request.company_scope = scope
    return scope
