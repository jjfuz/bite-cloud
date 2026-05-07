from dataclasses import dataclass

from django.core.exceptions import PermissionDenied

_SESSION_KEY = "_bite_company_scope"


@dataclass(frozen=True)
class RequestScope:
    tenant_id: str
    company_id: str


def get_request_scope(request) -> RequestScope:
    # 1. Cache por request (dentro del mismo ciclo HTTP, sin coste)
    if hasattr(request, "company_scope"):
        return request.company_scope

    user = request.user
    if not user.is_authenticated:
        raise PermissionDenied("Authentication required")

    # 2. Cache por sesion (evita llamada a Auth0/BD en cada request)
    cached = request.session.get(_SESSION_KEY)
    if cached:
        scope = RequestScope(**cached)
        request.company_scope = scope
        return scope

    # 3. Auth0 userinfo (cuando Auth0 esta configurado)
    tenant_id, company_id = _resolve_from_auth0(request)

    # 4. CompanyAccess model (auth local / tests)
    if not (tenant_id and company_id):
        tenant_id, company_id = _resolve_from_company_access(user)

    if not (tenant_id and company_id):
        raise PermissionDenied("No company access configured for this user")

    scope = RequestScope(tenant_id=tenant_id, company_id=company_id)
    request.session[_SESSION_KEY] = {"tenant_id": tenant_id, "company_id": company_id}
    request.company_scope = scope
    return scope


def _resolve_from_auth0(request):
    try:
        from monitoring.auth0backend import get_auth0_company_scope
        return get_auth0_company_scope(request)
    except Exception:
        return None, None


def _resolve_from_company_access(user):
    from common.models import CompanyAccess
    try:
        access = CompanyAccess.objects.only("tenant_id", "company_id").get(user=user)
        return access.tenant_id, access.company_id
    except CompanyAccess.DoesNotExist:
        return None, None
