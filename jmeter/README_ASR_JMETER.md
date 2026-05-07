# JMeter ASR: aislamiento por empresa y autenticacion

Este plan valida el ASR:

- Solo acceso a datos de la empresa propia.
- Denegacion de accesos cross-company.
- Denegacion de accesos sin autenticacion.
- Validacion de latencia menor a 200ms en cada solicitud protegida probada.

## Archivos

- Plan: `jmeter/asr_company_isolation_auth.jmx`
- Datos CSV: `jmeter/data/auth_users.csv`

## Datos requeridos

En `jmeter/data/auth_users.csv` debes tener usuarios locales validos (Django) y datos existentes:

- `username,password`: credenciales locales de `/accounts/login/`
- `expected_company_id`: company del usuario
- `authorized_scope_id`: scope valido de su empresa (ej: `company-001-project-001`)
- `unauthorized_scope_id`: scope de otra empresa (ej: `company-002-project-001`)
- `authorized_job_id`: job id que pertenezca a su empresa
- `unauthorized_job_id`: job id de otra empresa

## Ejecucion headless

```bash
jmeter -n -t jmeter/asr_company_isolation_auth.jmx \
  -JHOST=localhost -JPORT=8000 -JPROTOCOL=http \
  -JTHREADS=30 -JRAMP_UP=60 -JLOOPS=10 \
  -JUNAUTH_THREADS=10 -JUNAUTH_RAMP_UP=20 -JUNAUTH_LOOPS=10 \
  -JUSERS_CSV=jmeter/data/auth_users.csv \
  -JREPORT_YEAR=2026 -JREPORT_MONTH=4 \
  -JUNAUTH_SCOPE_ID=company-001-project-001 -JUNAUTH_JOB_ID=1 \
  -l jmeter/results/asr_results.jtl -e -o jmeter/results/asr_html
```

## Criterio de aceptacion sugerido

- 0 fallos de aserciones.
- 100% de requests bajo prueba con codigo esperado:
  - autorizados: 200
  - cross-company: 404
  - no autenticados: 401
- 100% de requests bajo prueba con latencia < 200ms (cada sampler tiene `Duration Assertion` de 200ms).

## Notas importantes

- Este plan usa login local para carga reproducible y estable.
- En despliegues con Auth0 activo, la autorizacion por empresa se valida igual porque el middleware/proteccion de endpoints es el mismo una vez existe sesion.
- Si quieres probar login federado Auth0 en carga, conviene un plan aparte por complejidad de redirects externos y anti-bot del IdP.
