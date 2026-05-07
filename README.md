# BITE Cloud

Despliegue de BITE Cloud con autenticación Auth0, aislamiento por compañía y despliegue AWS vía Terraform.

## Estado esperado del despliegue

- La rama de despliegue es `auth0`.
- Terraform crea el ALB, las 2 EC2 web, RabbitMQ, el consumer cloud y PostgreSQL RDS.
- Terraform también escribe el `.env` de las EC2 web, así que en un despliegue normal no hace falta entrar a editar variables a mano.
- El login web va por Auth0 cuando `auth0_domain`, `auth0_client_id` y `auth0_client_secret` están configurados.

## Flujo recomendado para el equipo

1. Crear la aplicación en Auth0.
2. Crear la Action post-login.
3. Crear al menos un usuario con `app_metadata` válido.
4. Crear `terraform/terraform.tfvars` con credenciales de Auth0.
5. Ejecutar `terraform apply`.
6. Probar login usando el DNS del ALB.

## Valores que sí muestran datos reales

Si usas el Terraform del repo tal como está, los datos sembrados y el scheduler trabajan con:

- `tenant_id = tenant-demo`
- `company_id = company-001` a `company-050` para datos de costos/reportes
- `company_id = company-001` a `company-039` para jobs generados por el scheduler

El primer usuario de prueba debería quedar así:

```json
{
  "tenant_id": "tenant-demo",
  "company_id": "company-001"
}
```

## Archivo recomendado: terraform/terraform.tfvars

```hcl
repo_branch         = "auth0"
auth0_domain        = "dev-XXXXXXXX.us.auth0.com"
auth0_client_id     = "TU_CLIENT_ID"
auth0_client_secret = "TU_CLIENT_SECRET"
```

## Problemas operativos que ya quedaron cubiertos

- Las dos EC2 web quedan apuntando a la misma base PostgreSQL, no a SQLite local.
- El target group del ALB queda con stickiness habilitado para estabilizar el callback de Auth0.
- Gunicorn arranca como servicio systemd desde `/opt/bite-cloud`.
- El scheduler queda solo en `reportes-manejador-reportes-1`.

## Si algo falla

- Si ves `User has no company access`, revisa el `app_metadata` del usuario en Auth0.
- Si el login redirige pero no ves datos, verifica que el usuario use `tenant-demo` y una `company_id` sembrada.
- Si el despliegue ya existía y mezclaba ramas, vuelve a ejecutar `terraform apply` con `repo_branch = "auth0"`.

## Guía detallada

La guía completa está en [AUTH0_SETUP.md](AUTH0_SETUP.md).