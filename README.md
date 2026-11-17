# Hito

Aplicación web para la gestión de memorias de título y tesis. Este documento cubre la ejecución local, los datos de prueba y las verificaciones del proyecto.

## Requisitos

- Docker Engine o Docker Desktop iniciado.
- Docker Compose v2.
- Node.js 22 para las verificaciones locales del frontend.

## Ejecución

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend python -m app.seed
```

Servicios disponibles:

- Aplicación web: <http://localhost:8080>
- API: <http://localhost:8000>
- Documentación OpenAPI: <http://localhost:8080/api/docs>
- Estado de la API: <http://localhost:8080/health/live>
- Estado de la base de datos: <http://localhost:8080/health/ready>

El backend ejecuta `alembic upgrade head` al iniciar. El seed es idempotente y crea 16 usuarios, 20 proyectos, 247 entregables y actividad de demostración: entregas, revisiones, mensajes de foro y adjuntos PDF sintéticos. No elimina datos existentes; si vuelves a ejecutarlo, solo agrega lo que falte.

La configuración local se toma de `.env`; revisa `.env.example` si necesitas cambiar credenciales, sesión, entorno o almacenamiento.

## Cuentas de prueba

| Correo | Tipo |
|---|---|
| `camila.soto@udec.cl` | Profesor |
| `rodrigo.pena@udec.cl` | Profesor |
| `antonio.skorin@udec.cl` | Profesor |
| `paula.herrera@udec.cl` | Profesor |
| `cristian.munoz@udec.cl` | Profesor |
| `javiera.contreras@udec.cl` | Estudiante |
| `benjamin.aravena@udec.cl` | Estudiante |
| `matias.riquelme@udec.cl` | Estudiante |
| `fernanda.torres@udec.cl` | Estudiante |
| `valentina.rojas@udec.cl` | Estudiante |
| `ignacio.fuentes@udec.cl` | Estudiante |
| `martina.lagos@udec.cl` | Estudiante |
| `tomas.sepulveda@udec.cl` | Estudiante |
| `isidora.paredes@udec.cl` | Estudiante |
| `diego.salazar@udec.cl` | Estudiante |
| `sebastian.vera@udec.cl` | Estudiante |

Todas las cuentas usan la contraseña `1234`. La cuenta principal para la demo es `camila.soto@udec.cl`, que gestiona 8 proyectos y tiene una bandeja de revisiones poblada. La contraseña se imprime al ejecutar `python -m app.seed` y el smoke test la lee desde `app.seed.DEMO_PASSWORD`. Son cuentas sintéticas y no deben reutilizarse en producción.

## Desarrollo del frontend

El contenedor `web` sirve el build de producción. Para trabajar con watch:

```bash
docker compose up -d db backend
cd frontend
npm ci
npm run dev
```

Vite queda en <http://localhost:5173> y reenvía `/api` y `/health` a <http://localhost:8000>.

Después de cambios en el frontend, reconstruye el contenedor web:

```bash
docker compose up --build -d web
```

## Tests y verificaciones

Pruebas del backend:

```bash
docker compose --profile test run --rm backend-test
```

Lint, formato y tipos del backend:

```bash
docker compose --profile test run --rm --entrypoint /bin/sh backend-test \
  -c "ruff check app tests alembic && ruff format --check app tests alembic && pyright"
```

Verificaciones del frontend:

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm run test:run
npm run build
```

Cobertura de la lógica de negocio (RNF-M-1):

```bash
./scripts/nfr/coverage.sh
```

La puerta falla bajo 80 % y deja reportes en `reports/nfr/coverage/` (`coverage.xml` y HTML).

Smoke test del stack completo con Docker Compose:

```bash
./scripts/nfr/compose_smoke.sh
```

El script valida la configuración, construye y levanta `db`, `backend` y `web`, espera `/health/ready`, ejecuta el seed, comprueba la SPA e inicia sesión con una cuenta demo. Deja el stack levantado para inspección; usa `SMOKE_CLEANUP=1 ./scripts/nfr/compose_smoke.sh` para eliminarlo al terminar.

Perfil TLS local con certificados autofirmados (RNF-S-3):

```bash
./scripts/nfr/tls_smoke.sh
```

El perfil usa `compose.tls.yaml` en un proyecto Compose separado (`hito_tls`), expone HTTPS en `8443` y HTTP en `8081`, y verifica TLS 1.2/1.3, rechazo de TLS 1.0/1.1, HSTS, redirección y cookie `Secure`. Para limpiar el stack: `TLS_CLEANUP=1 ./scripts/nfr/tls_smoke.sh`. El proxy Nginx/Certbot, la renovación y la auditoría SSL Labs quedan documentados en `docs/operations/tls.md`.

Reporte de almacenamiento y crecimiento (RNF-R-3):

```bash
./scripts/nfr/storage_report.sh
```

El reporte compara el volumen de subidas con los metadatos de PostgreSQL, aplica una cuota de 100 GB y alerta al 80 % o ante una diferencia mayor a 5 %. Escribe `reports/nfr/storage.json` y usa códigos de salida `0` (ok), `2` (warning) y `1` (critical). Los pasos de S3, ciclo de vida y AWS Budgets están en `docs/operations/storage.md`.

Respaldo y simulacro de restauración (RNF-D-2):

```bash
./scripts/nfr/backup.sh
./scripts/nfr/restore_drill.sh
```

`backup.sh` crea en `backups/` un dump de PostgreSQL, un archivo `tar --sparse` de las subidas y un manifiesto con SHA-256, tamaños y conteos. `restore_drill.sh` verifica el respaldo, lo restaura en un PostgreSQL desechable, compara conteos y archivos, y escribe `reports/nfr/restore-drill.json`. Los detalles, la retención de 30 días y los pasos de producción están en `docs/operations/backup-restore.md`.

## Pruebas E2E y accesibilidad

El stack E2E es independiente (`hito_e2e`, puerto `18080`) y usa una base `hito_e2e`; no toca los datos de desarrollo.

```bash
# Chromium, como en CI
./scripts/nfr/e2e.sh --project=chromium

# Matriz completa Chromium + Firefox + WebKit
./scripts/nfr/e2e.sh
```

El script reinicia el stack E2E, lo construye, ejecuta el seed y corre Playwright. Para limpiar al terminar: `E2E_CLEANUP=1 ./scripts/nfr/e2e.sh --project=chromium`.

Las pruebas cubren PA-1, PA-2, PA-4 y PA-5, axe-core WCAG 2.1 A/AA en Chromium, teclado/foco y diseño a 360 px. Firefox y WebKit ejecutan el smoke funcional y los flujos; la matriz completa corre en nightly. Si WebKit falla localmente por dependencias del sistema, instala con `sudo npx playwright install-deps webkit` o deja que CI las instale. La checklist manual de WCAG está en `docs/nfr/wcag-manual-checklist.md`.

## Validación de usabilidad

La validación con profesores es manual y se ejecuta después de las pruebas automatizadas:

- protocolo: `docs/nfr/usability-protocol.md`;
- cuestionario SUS: `docs/nfr/sus-form.md`;
- planilla de resultados: `docs/nfr/results-template.md`;
- consentimiento: Anexo H de `spec/main.tex`.

Criterios: ≥ 85 % de las tareas PA-1, PA-2 y PA-5 completadas sin ayuda en el primer intento, y SUS ≥ 68. Los resultados agregados se registran en el Anexo B.

## Rendimiento y memoria

El stack de rendimiento es independiente (`hito_perf`, puerto `18081`) y siembra el escenario SRS completo: 675 cuentas, 529 proyectos, 5.290 entregables, 13.225 entregas y 6.615 archivos dispersos.

```bash
# Ejecución completa: 100 usuarios durante 15 minutos
PERF_CLEANUP=1 ./scripts/nfr/perf.sh

# Smoke rápido para verificar la infraestructura
PERF_USERS=10 PERF_DURATION=30 PERF_RAMP_UP=5 PERF_CLEANUP=1 ./scripts/nfr/perf.sh
```

Genera:

- `reports/nfr/load.json` y `load.md`: p50/p95/p99, errores, throughput y mezcla de carga;
- `reports/nfr/navigation.json`: navegación Playwright y subida de 10 MB;
- `reports/nfr/memory.json`: pico y media de RAM de `backend`, `db` y `web`, con instancia AWS sugerida.

La RAM se muestrea con `docker stats` y se incluye en `load.json`. Para estimar AWS, toma `peak_total_mib`, suma 30 % y elige la instancia más pequeña que cubra esa memoria; en el VPS confirma con `free -m`/CloudWatch. Los detalles y el límite de USD 10 están en `docs/operations/performance.md`.

El workflow `.github/workflows/perf-vps.yml` ejecuta la carga contra un VPS por `workflow_dispatch`; con `enforce=yes` falla si p95 > 500 ms o la tasa de error es ≥ 1 %.

## Integración continua

`.github/workflows/ci.yml` se ejecuta en cada push a `main` y en cada pull request. Incluye:

- lint, formato y tipos del backend;
- pruebas del backend y puerta de cobertura de 80 %;
- lint, tipos, tests y build del frontend;
- smoke test de Docker Compose con los logs como artefacto si falla;
- perfil TLS local con handshake TLS 1.2/1.3, HSTS y cookie `Secure`;
- E2E Chromium con PA-1/PA-2/PA-4/PA-5, axe y 360 px.

Los reportes de cobertura se publican como artefacto `backend-coverage`. Los reportes locales viven en `reports/`, que está ignorado por Git.

`.github/workflows/nfr-nightly.yml` ejecuta a diario, o bajo demanda, el respaldo y simulacro de restauración, el reporte de almacenamiento, la matriz E2E de Chromium/Firefox/WebKit y el reporte de rendimiento completo. Publica `restore-drill-report`, `backup-manifest`, `storage-report`, `playwright-all-browsers`, `performance-report` y sus logs como artefactos.

### CI remoto por SSH

El repositorio incluye un runner para ejecutar el CI completo en una máquina Linux externa:

```bash
./scripts/ci/remote-ci.sh usuario@servidor
```

El wrapper copia el árbol de trabajo por `rsync`, ejecuta el CI en el servidor y descarga los reportes a `reports/ci/<timestamp>/`.

Perfiles disponibles:

```bash
# CI de cada PR (por defecto)
./scripts/ci/remote-ci.sh usuario@servidor

# Respaldo/restauración, almacenamiento, todos los navegadores y rendimiento
./scripts/ci/remote-ci.sh usuario@servidor --profile nightly

# Ambos perfiles
./scripts/ci/remote-ci.sh usuario@servidor --profile all
```

También se puede ejecutar directamente en el servidor:

```bash
ssh usuario@servidor
cd hito-ci
./scripts/ci/run-ci.sh --profile pr
```

Requisitos del servidor: Docker Engine con Compose v2.24+, Node.js 22 con npm, Python 3.10+, `curl`, `rsync` y acceso al daemon de Docker. El runner usa el proyecto Compose aislado `hito_ci`; nunca usa el proyecto de producción `hito`. Requiere que los puertos `8000`, `8080`, `18080`, `8081`, `8443` y, en modo nightly, `18081` estén libres.

El runner verifica prerequisitos, valida las configuraciones Compose, ejecuta cada etapa, recopila reportes y limpia los contenedores al terminar. Usa `--keep` para conservarlos y `--skip-port-check` solo si controlas manualmente los puertos.

### Despliegue demo por SSH

El workflow `.github/workflows/ci.yml` incluye un job `deploy-demo` que se ejecuta después de que todo el CI pasa, solo en `main` o por ejecución manual. El despliegue usa el proyecto Compose `hito` para la aplicación, un proxy Nginx separado (`hito_proxy`) en los puertos `80`/`443` y datos de demostración creados con `python -m app.seed`.

Requisitos en GitHub:

- Secret `SSH_HOST`: host SSH, por ejemplo `hitoapp.ddns.net`.
- Secret `SSH_USER`: usuario SSH, por ejemplo `fgonzalez`.
- Secret `SSH_PRIVATE_KEY`: clave privada SSH.
- Secret `SSH_KNOWN_HOSTS`: salida de `ssh-keyscan -H <host>` (recomendado).
- Secret opcional `SSH_PORT`.
- Secret opcional `CERTBOT_EMAIL`: correo para Let’s Encrypt; si falta, se usa registro sin correo.
- Variable opcional `DEPLOY_PATH`: directorio remoto, por defecto `hito`.
- Variable opcional `DEMO_DOMAIN`: dominio público, por defecto `hitoapp.ddns.net`.
- Variable opcional `DEMO_INTERNAL_PORT`: puerto loopback del contenedor web, por defecto `9080`.
- Variable opcional `ENABLE_HTTPS`: `1` por defecto; usa `0` para omitir Nginx/TLS.

El despliegue manual se puede ejecutar desde el repositorio:

```bash
./scripts/cd/remote-deploy.sh fgonzalez@hitoapp.ddns.net
```

El script:

- sincroniza el árbol de trabajo a `DEPLOY_PATH` por `rsync`;
- conserva el `.env.demo` remoto y las credenciales de la base;
- construye y levanta `compose.yaml` con `compose.demo.yaml` en `127.0.0.1:9080`;
- espera `/health/ready`, ejecuta el seed y verifica el login demo;
- levanta `compose.proxy.yaml` con Nginx en `80`/`443`;
- obtiene o reutiliza el certificado Let’s Encrypt del dominio;
- activa `SESSION_COOKIE_SECURE=true` y `TRUST_PROXY_HEADERS=true`;
- redirige HTTP a HTTPS;
- no ejecuta `down -v` ni borra los datos existentes.

El demo queda disponible en `https://hitoapp.ddns.net`. Los puertos `80` y `443` deben estar reenviados desde el router al host: `80` se usa para el desafío ACME y la redirección, y `443` para HTTPS. Es solo para demostración; no debe tratarse como un despliegue de producción con datos reales.

Si `https://hitoapp.ddns.net` presenta un certificado distinto de `CN=hitoapp.ddns.net`, el puerto `443` no está llegando al host. En ese caso revisa el port forwarding del router o desactiva la administración remota del router en el puerto `443`. Para verificar desde fuera:

```bash
curl -I http://hitoapp.ddns.net/
curl -I https://hitoapp.ddns.net/
```

La primera debe devolver `301` hacia HTTPS; la segunda debe validar el certificado y devolver `200`.

### Renovación del certificado

El certificado Let's Encrypt se renueva con:

```bash
./scripts/cd/renew-certificates.sh
```

Para validar el flujo sin cambiar el certificado instalado:

```bash
./scripts/cd/renew-certificates.sh --dry-run
```

Se recomienda programar una ejecución diaria en el servidor:

```bash
crontab -e
```

```cron
17 3 * * * cd /home/fgonzalez/hito && ./scripts/cd/renew-certificates.sh >> renew.log 2>&1
```

El script renueva solo si corresponde y recarga Nginx. El puerto `80` sigue disponible para el desafío ACME.

Si el puerto `443` no está accesible, puedes usar un túnel SSH al proxy como alternativa privada:

```bash
ssh -N -L 8080:127.0.0.1:443 fgonzalez@hitoapp.ddns.net
```

y abrir `https://localhost:8080` (el certificado será para `hitoapp.ddns.net` y el navegador puede pedir una excepción).

## Comandos útiles

```bash
docker compose config
docker compose ps
docker compose logs -f backend web
docker compose exec backend alembic current
docker compose down
```

Para reiniciar la base de datos y los archivos desde cero, eliminando todos los datos:

```bash
docker compose down -v
docker compose up --build -d
docker compose exec backend python -m app.seed
```

## Estructura

- `backend/` — API FastAPI, modelos SQLAlchemy, migraciones Alembic y tests.
- `frontend/` — aplicación React + TypeScript/Vite y tests Vitest.
- `db/init/` — inicialización de PostgreSQL.
- `compose.yaml` — servicios de base de datos, backend, web y tests.
- `compose.tls.yaml` — perfil TLS autofirmado para pruebas locales.
- `compose.e2e.yaml` — stack E2E aislado en el puerto `18080`.
- `compose.perf.yaml` — stack de rendimiento aislado en el puerto `18081`.
- `compose.demo.yaml` — demo interno en `127.0.0.1:9080`, sin exponer el backend.
- `compose.proxy.yaml` — Nginx y Certbot en los puertos `80`/`443`.
- `deploy/nginx/` — plantillas HTTP/HTTPS del proxy.
- `scripts/ci/` — runner de CI local y wrapper para ejecutar el CI completo por SSH.
- `scripts/cd/` — despliegue demo por SSH, proxy TLS y sincronización del árbol de trabajo.
- `scripts/nfr/` — verificación de requisitos no funcionales: cobertura, smoke, TLS, almacenamiento, respaldos, E2E y rendimiento.
- `.github/workflows/` — integración continua y jobs nightly.
- `docs/operations/` — runbooks de operación, incluidos TLS, almacenamiento, respaldos y rendimiento.
- `docs/nfr/` — checklist manual de WCAG, protocolo de usabilidad, SUS y plantilla de resultados.
- `reports/` — reportes generados localmente; ignorado por Git.
- `certs/` — certificados autofirmados generados; ignorado por Git.
- `backups/` — respaldos locales; ignorado por Git por contener datos personales.
