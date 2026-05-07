from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, JsonResponse

from common.auth import get_request_scope


class AnalysisAccessMiddleware:
    PROTECTED_PREFIXES = (
        "/reports/",
        "/api/jobs/",
        "/dashboard/",
    )
    PROTECTED_EXACT_PATHS = {
        "/",
    }
    ALLOWED_PREFIXES = (
        "/health/",
        "/admin/",
        "/accounts/",
        "/static/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if self._is_allowed_without_auth(path):
            return self.get_response(request)

        if not self._is_protected(path):
            return self.get_response(request)

        if not request.user.is_authenticated:
            if self._is_api_request(path):
                return JsonResponse({"error": "Authentication required"}, status=401)
            return redirect_to_login(path)

        try:
            get_request_scope(request)
        except PermissionDenied:
            if self._is_api_request(path):
                return JsonResponse({"error": "User has no company access"}, status=403)
            return HttpResponseForbidden("User has no company access")

        return self.get_response(request)

    def _is_api_request(self, path: str) -> bool:
        return path.startswith("/reports/") or path.startswith("/api/")

    def _is_allowed_without_auth(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.ALLOWED_PREFIXES)

    def _is_protected(self, path: str) -> bool:
        if path in self.PROTECTED_EXACT_PATHS:
            return True
        return any(path.startswith(prefix) for prefix in self.PROTECTED_PREFIXES)
