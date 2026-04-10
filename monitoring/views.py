from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from reports.models import OrphanEBSSnapshot

def health(request):
    return JsonResponse({"status": "ok"})

def orphan_report_detail_json(request, sample_row_id: int):
    try:
        # 1. Buscamos el registro base
        sample_row = get_object_or_404(OrphanEBSSnapshot, id=sample_row_id)

        # 2. Filtramos los registros relacionados
        rows = OrphanEBSSnapshot.objects.filter(
            tenant_id=sample_row.tenant_id,
            company_id=sample_row.company_id,
            project_id=sample_row.project_id,
            snapshot_date=sample_row.snapshot_date,
            generated_at=sample_row.generated_at,
        ).order_by("ranking_position", "volume_id")

        # 3. Serializamos los datos
        items = [
            {
                "volume_id": row.volume_id,
                "volume_name": row.volume_name,
                "region": row.region,
                "size_gib": row.size_gib,
                "monthly_cost": float(row.monthly_cost) if row.monthly_cost else 0.0,
                "currency": row.currency,
                "ranking_position": row.ranking_position,
            }
            for row in rows
        ]

        return JsonResponse({"data": items}, safe=False)

    except Exception as e:
        # Si algo falla aquí, lo veremos en la respuesta
        return JsonResponse({"error_interno": str(e)}, status=500)
