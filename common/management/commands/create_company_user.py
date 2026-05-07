from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from common.models import CompanyAccess


class Command(BaseCommand):
    help = "Crea o actualiza un usuario y lo asocia a un tenant/company."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--tenant-id", required=True)
        parser.add_argument("--company-id", required=True)
        parser.add_argument("--email", default="")
        parser.add_argument("--is-staff", action="store_true")

    def handle(self, *args, **options):
        user_model = get_user_model()
        username = options["username"]
        password = options["password"]
        tenant_id = options["tenant_id"]
        company_id = options["company_id"]
        email = options["email"]

        if not username.strip():
            raise CommandError("username no puede ser vacio")

        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )

        if created:
            user.set_password(password)
            user.is_staff = options["is_staff"]
            user.save(update_fields=["password", "is_staff"])
        else:
            user.set_password(password)
            if email:
                user.email = email
            if options["is_staff"]:
                user.is_staff = True
            user.save()

        access, _ = CompanyAccess.objects.update_or_create(
            user=user,
            defaults={"tenant_id": tenant_id, "company_id": company_id},
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Usuario {user.username} asociado a tenant={access.tenant_id} company={access.company_id}"
            )
        )
