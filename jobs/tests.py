from django.contrib.auth.models import User
from django.test import TestCase

from common.models import CompanyAccess
from jobs.models import ScheduledJobExecution


class JobAccessTests(TestCase):
	def setUp(self):
		user_one = User.objects.create_user(username="user1", password="secret")
		user_two = User.objects.create_user(username="user2", password="secret")

		CompanyAccess.objects.create(user=user_one, tenant_id="tenant-demo", company_id="company-001")
		CompanyAccess.objects.create(user=user_two, tenant_id="tenant-demo", company_id="company-002")

		self.job_company_one = ScheduledJobExecution.objects.create(
			job_key="job-001",
			job_type=ScheduledJobExecution.JOB_REFRESH_FINANCIAL_REPORT,
			tenant_id="tenant-demo",
			company_id="company-001",
			status=ScheduledJobExecution.STATUS_SUCCEEDED,
		)
		self.job_company_two = ScheduledJobExecution.objects.create(
			job_key="job-002",
			job_type=ScheduledJobExecution.JOB_REFRESH_ORPHAN_EBS,
			tenant_id="tenant-demo",
			company_id="company-002",
			status=ScheduledJobExecution.STATUS_SUCCEEDED,
		)

	def test_job_api_requires_authentication(self):
		response = self.client.get(f"/api/jobs/{self.job_company_one.id}/")
		self.assertEqual(response.status_code, 401)

	def test_user_can_only_access_own_company_jobs(self):
		self.client.login(username="user1", password="secret")

		own_response = self.client.get(f"/api/jobs/{self.job_company_one.id}/")
		self.assertEqual(own_response.status_code, 200)

		cross_company_response = self.client.get(f"/api/jobs/{self.job_company_two.id}/")
		self.assertEqual(cross_company_response.status_code, 404)
