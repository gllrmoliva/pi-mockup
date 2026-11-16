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

El backend ejecuta `alembic upgrade head` al iniciar. El seed es idempotente y crea 7 usuarios, 4 proyectos y 7 entregables de ejemplo.

La configuración local se toma de `.env`; revisa `.env.example` si necesitas cambiar credenciales, sesión, entorno o almacenamiento.

## Cuentas de prueba

| Correo | Tipo |
|---|---|
| `camila.soto@udec.cl` | Profesor |
| `rodrigo.pena@udec.cl` | Profesor |
| `javiera.contreras@udec.cl` | Estudiante |
| `benjamin.aravena@udec.cl` | Estudiante |
| `matias.riquelme@udec.cl` | Estudiante |
| `fernanda.torres@udec.cl` | Estudiante |
| `antonio.skorin@udec.cl` | Profesor |

La contraseña de demostración es `HitoDemo123!`. Son cuentas sintéticas y no deben reutilizarse en producción.

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
