# Configuración de Auth0 para BITE Cloud

Este documento explica cómo cada integrante del equipo debe configurar su propia cuenta de Auth0 para desplegar la aplicación con autenticación.

---

## Requisitos previos

- Tener una cuenta de AWS con acceso al laboratorio.
- Haber hecho `terraform apply` al menos una vez para tener el ALB levantado y conocer su DNS.
- El DNS del ALB lo obtienes del output de Terraform:
  ```
  alb_reportes_dns = "reportes-alb-XXXXXXXXX.us-east-1.elb.amazonaws.com"
  ```

---

## Paso 1 – Crear cuenta y tenant en Auth0

1. Ve a [https://auth0.com/](https://auth0.com/) y crea una cuenta (puedes usar GitHub).
2. Al crear la cuenta, Auth0 crea automáticamente un **tenant**. El nombre del tenant se ve en la esquina superior izquierda del dashboard, con formato `dev-XXXXXXXX`.
3. El **dominio** de tu tenant es `dev-XXXXXXXX.us.auth0.com`. Lo necesitarás más adelante.

---

## Paso 2 – Crear la aplicación en Auth0

1. En el menú lateral: **Applications → Applications → Create Application**
2. Nombre: `bite-cloud` (o el que prefieras)
3. Tipo: **Regular Web Application**
4. Click en **Create**
5. Ve a la pestaña **Settings** de la aplicación recién creada y anota estos tres valores:
   - **Domain** → `dev-XXXXXXXX.us.auth0.com`
   - **Client ID**
   - **Client Secret**

6. En la misma pantalla, configura las URLs (reemplaza con el DNS de tu ALB):
   - **Allowed Callback URLs:**
     ```
     http://TU_ALB_DNS/complete/auth0
     ```
   - **Allowed Logout URLs:**
     ```
     http://TU_ALB_DNS
     ```
   - **Allowed Web Origins:**
     ```
     http://TU_ALB_DNS
     ```
7. Click en **Save Changes**

---

## Paso 3 – Habilitar Authorization Code

1. En la misma aplicación, baja hasta **Advanced Settings** (al final de Settings)
2. Pestaña **Grant Types**
3. Marca **Authorization Code**
4. Click en **Save Changes**

---

## Paso 4 – Crear la Action post-login (inyecta empresa en el token)

Auth0 no incluye el `app_metadata` del usuario en el token por defecto. Hay que crear una Action que lo inyecte.

1. Menú lateral: **Actions → Triggers → post-login**
2. En la pestaña **Custom**, click en **Create Action**
3. Nombre: `Inject Company Scope`
4. Pega este código, **reemplazando `TU_DOMINIO` por tu dominio real** (ej: `dev-XXXXXXXX.us.auth0.com`):

```javascript
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'TU_DOMINIO';
  if (event.user.app_metadata) {
    api.accessToken.setCustomClaim(
      `${namespace}/tenant_id`,
      event.user.app_metadata.tenant_id
    );
    api.accessToken.setCustomClaim(
      `${namespace}/company_id`,
      event.user.app_metadata.company_id
    );
  }
};
```

5. Click en **Deploy** (esquina superior derecha)
6. Vuelve al flow: **Actions → Triggers → post-login**
7. En la pestaña **Custom**, arrastra la acción `Inject Company Scope` al flujo, entre **Start** y **Complete**
8. Click en **Apply**

---

## Paso 5 – Crear usuarios en Auth0

Los usuarios de Auth0 representan a las personas que acceden al dashboard. Cada usuario debe estar asociado a una empresa (`company_id`) que exista en la base de datos.

### Cómo ver las empresas disponibles en la BD

Una vez que la infraestructura esté levantada, entra por SSH al nodo reportes-1 y corre:

```bash
cd /opt/bite-cloud
./.venv/bin/python manage.py shell -c "
from cloud.models import RawCostRecord
companies = RawCostRecord.objects.values_list('company_id', flat=True).distinct().order_by('company_id')[:20]
print(list(companies))
"
```

Verás algo como: `['company-001', 'company-002', ..., 'company-050']`

### Crear un usuario

1. Menú lateral: **User Management → Users → Create User**
2. Ingresa email y contraseña (el email no tiene que existir realmente)
3. Connection: `Username-Password-Authentication`
4. Click en **Create**

### Asignar empresa al usuario

1. Entra al usuario recién creado
2. Busca la sección **App Metadata**
3. Pega el siguiente JSON (ajusta `company_id` según la empresa que quieres asignar):

```json
{
  "tenant_id": "tenant-demo",
  "company_id": "company-001"
}
```

4. Click en **Save**

Repite este proceso para cada usuario que necesites. Usuarios con diferente `company_id` solo podrán ver los datos de su propia empresa.

---

## Paso 6 – Desplegar con Terraform

Crea el archivo `terraform/terraform.tfvars` en tu máquina local con tus credenciales de Auth0. **Este archivo NO debe subirse al repositorio.**

```hcl
# terraform/terraform.tfvars
auth0_domain        = "dev-XXXXXXXX.us.auth0.com"
auth0_client_id     = "TU_CLIENT_ID"
auth0_client_secret = "TU_CLIENT_SECRET"
```

Luego despliega normalmente:

```bash
cd terraform
terraform init
terraform apply
```

Terraform inyecta esas variables automáticamente al `.env` de las EC2 y el `APP_BASE_URL` se resuelve solo con el DNS del ALB.

> **Alternativa sin archivo tfvars** (si prefieres pasar las variables directo):
> ```bash
> terraform apply \
>   -var="auth0_domain=dev-XXXXXXXX.us.auth0.com" \
>   -var="auth0_client_id=TU_CLIENT_ID" \
>   -var="auth0_client_secret=TU_CLIENT_SECRET"
> ```

---

## Paso 7 – Verificar que funciona

1. Abre `http://TU_ALB_DNS/` en el navegador
2. Debes ver la pantalla de login con el botón **Continuar con Auth0**
3. Al hacer click, te redirige al login de Auth0
4. Ingresa con un usuario que hayas creado en el Paso 5
5. Después del login debes volver al dashboard y ver solo los datos de la empresa asignada al usuario

### Pruebas de aislamiento

- Crea dos usuarios con diferente `company_id`
- Verifica que cada uno solo ve sus propios reportes y jobs
- Intenta acceder a `/reports/financial/...` sin login → debe responder `401`

---

## Resumen de dónde encontrar cada valor

| Variable | Dónde encontrarla |
|---|---|
| `auth0_domain` | Auth0 Dashboard → Applications → tu app → Settings → **Domain** |
| `auth0_client_id` | Auth0 Dashboard → Applications → tu app → Settings → **Client ID** |
| `auth0_client_secret` | Auth0 Dashboard → Applications → tu app → Settings → **Client Secret** |
| `APP_BASE_URL` | Output de Terraform: `alb_reportes_dns` (se configura automáticamente) |

---

## Importante: archivos que NO deben subirse al repo

Asegúrate de que tu `.gitignore` incluya:

```
terraform/terraform.tfvars
terraform/.terraform/
terraform/*.tfstate
terraform/*.tfstate.backup
.env
```
