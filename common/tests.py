from django.contrib.auth.models import User
from django.test import TestCase

from common.models import CompanyAccess


class DashboardAuthTests(TestCase):
    def test_dashboard_redirects_when_unauthenticated(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)

    def test_dashboard_allows_authenticated_company_user(self):
        user = User.objects.create_user(username="u1", password="secret")
        CompanyAccess.objects.create(user=user, tenant_id="tenant-demo", company_id="company-001")

        self.client.login(username="u1", password="secret")
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
