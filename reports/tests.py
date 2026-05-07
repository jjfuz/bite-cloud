from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from common.models import CompanyAccess
from reports.models import FinancialReportSnapshot


class ReportAccessTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="viewer", password="secret")
		CompanyAccess.objects.create(user=self.user, tenant_id="tenant-demo", company_id="company-001")

		FinancialReportSnapshot.objects.create(
			tenant_id="tenant-demo",
			company_id="company-001",
			scope_type="project",
			scope_id="company-001-project-001",
			period_year=2026,
			period_month=4,
			report_type=FinancialReportSnapshot.REPORT_TYPE_MONTHLY,
			currency="USD",
			total_cost=100,
			report_payload={"ok": True},
			generated_at=timezone.now(),
			is_current=True,
		)

		FinancialReportSnapshot.objects.create(
			tenant_id="tenant-demo",
			company_id="company-002",
			scope_type="project",
			scope_id="company-002-project-001",
			period_year=2026,
			period_month=4,
			report_type=FinancialReportSnapshot.REPORT_TYPE_MONTHLY,
			currency="USD",
			total_cost=200,
			report_payload={"ok": True},
			generated_at=timezone.now(),
			is_current=True,
		)

	def test_reports_require_authentication(self):
		response = self.client.get("/reports/financial/project/company-001-project-001/?year=2026&month=4")
		self.assertEqual(response.status_code, 401)

	def test_user_can_read_only_own_company_report(self):
		self.client.login(username="viewer", password="secret")

		own_response = self.client.get(
			"/reports/financial/project/company-001-project-001/?year=2026&month=4"
		)
		self.assertEqual(own_response.status_code, 200)

		other_response = self.client.get(
			"/reports/financial/project/company-002-project-001/?year=2026&month=4"
		)
		self.assertEqual(other_response.status_code, 404)
