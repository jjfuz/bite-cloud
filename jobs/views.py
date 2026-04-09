from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from .models import ScheduledJobExecution

def job_detail_api(request, job_id):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        job = ScheduledJobExecution.objects.get(id=job_id)

        data = {
            "id": job.id,
            "status": job.status,
            "job_type": job.job_type,
            "job_key": job.job_key,
            "tenant": job.tenant_id,
            "company": job.company_id,
            "project": job.project_id,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "error": job.error_message,
        }

        return JsonResponse(data)

    except ScheduledJobExecution.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)
