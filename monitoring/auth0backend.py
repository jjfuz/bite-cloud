import requests
from django.conf import settings
from social_core.backends.oauth import BaseOAuth2


class Auth0(BaseOAuth2):
    """Auth0 OAuth2 authentication backend (siguiendo patron ISIS2503)."""

    name = "auth0"
    SCOPE_SEPARATOR = " "
    ACCESS_TOKEN_METHOD = "POST"
    EXTRA_DATA = [
        ("picture", "picture"),
        ("access_token", "access_token"),
    ]

    def authorization_url(self):
        return "https://" + self.setting("DOMAIN") + "/authorize"

    def access_token_url(self):
        return "https://" + self.setting("DOMAIN") + "/oauth/token"

    def get_user_id(self, details, response):
        return details["user_id"]

    def get_user_details(self, response):
        url = "https://" + self.setting("DOMAIN") + "/userinfo"
        headers = {"authorization": "Bearer " + response["access_token"]}
        resp = requests.get(url, headers=headers, timeout=5)
        userinfo = resp.json()
        return {
            "username": userinfo["nickname"],
            "first_name": userinfo["name"],
            "picture": userinfo.get("picture", ""),
            "user_id": userinfo["sub"],
        }


def get_auth0_company_scope(request):
    """
    Lee tenant_id y company_id desde los custom claims del token de Auth0.
    Los claims son inyectados por la Action post-login con namespace = dominio Auth0.
    Retorna (tenant_id, company_id) o (None, None) si no estan disponibles.
    """
    domain = getattr(settings, "SOCIAL_AUTH_AUTH0_DOMAIN", "")
    if not domain:
        return None, None

    try:
        auth0user = request.user.social_auth.filter(provider="auth0")[0]
        access_token = auth0user.extra_data["access_token"]
        url = f"https://{domain}/userinfo"
        headers = {"authorization": f"Bearer {access_token}"}
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        info = resp.json()
        tenant_id = info.get(f"{domain}/tenant_id") or ""
        company_id = info.get(f"{domain}/company_id") or ""
        return (tenant_id or None), (company_id or None)
    except Exception:
        return None, None
