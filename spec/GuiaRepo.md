# GuiaRepo — Repository guide

This guide maps the repository so developers and testers can quickly find where each kind of change belongs.

## Mental model

```text
Browser / React SPA
        │
        ▼
Nginx :8080 ──/api/*──▶ FastAPI :8000 ──▶ PostgreSQL
                              │
                              └──▶ uploads_data volume
```

- The frontend lives in `frontend/`.
- The API and domain logic live in `backend/app/`.
- PostgreSQL schema is managed with Alembic.
- Uploaded files are stored outside PostgreSQL, in local storage.
- Domain/database naming is mostly Spanish; API JSON and TypeScript types are English. Conversion maps live in the backend schemas.

## Top level

| Path | Purpose |
|---|---|
| `backend/` | FastAPI application, migrations, tests and backend Docker build. |
| `frontend/` | React + TypeScript/Vite SPA, tests, styles and Nginx build. |
| `db/init/` | PostgreSQL initialization scripts. Creates the `hito_test`, `hito_e2e` and `hito_perf` databases. |
| `compose.yaml` | Main runtime: `db`, `backend`, `web` and `backend-test` services. |
| `compose.tls.yaml` | Self-signed TLS override for local verification. |
| `compose.e2e.yaml` | Isolated E2E stack on port `18080`. |
| `compose.perf.yaml` | Isolated performance stack on port `18081`. |
| `compose.demo.yaml` | Demo stack on loopback port `9080`, with the backend not exposed. |
| `compose.proxy.yaml` | Nginx/Certbot host proxy on ports `80` and `443`. |
| `deploy/nginx/` | HTTP/HTTPS Nginx templates for the demo proxy. |
| `proxy/` | Generated proxy config and Let’s Encrypt certificates; ignored by Git. |
| `docs/operations/` | Operational runbooks, including TLS, storage, backups, restores and performance. |
| `docs/nfr/` | Manual NFR evidence: WCAG checklist, usability protocol, SUS and results template. |
| `.env.example` | Configuration template. Copy it to `.env` for local runs. |
| `.env` | Local configuration; ignored by Git. |
| `README.md` | Developer/tester guide: run, test and useful commands. |
| `.github/workflows/` | GitHub Actions: CI, nightly NFR jobs and manual VPS performance. |
| `scripts/ci/` | Remote CI runner and local SSH wrapper with PR/nightly/all profiles. |
| `scripts/cd/` | Demo deployment over SSH, with remote sync and seed-only setup. |
| `scripts/nfr/` | NFR verification scripts: coverage, smoke, TLS, storage, backups, E2E and performance. |
| `reports/` | Generated coverage/smoke reports; ignored by Git. |
| `backups/` | Local database/uploads backups and manifests; ignored by Git. |
| `spec/GuiaRepo.md` | This repository map and change-location guide. |
| `spec/hito-must-build-spec.md` | Main implementation specification and source of truth for Must-RF behavior. |
| `spec/ComponentC4.svg` | Architecture/component diagram. |
| `spec/main.tex` | LaTeX SRS/report document. Documentation, not runtime code. |
| `spec/nfr-test-plan.md` | NFR verification plan and check matrix. |
| `spec/main-tex-nfr-changes.md` | Proposed SRS changes and implementation status. |
| `deprecated-mockup/` | Static visual/reference mockup. Not served by Docker and not part of the current app. |

## Backend

```text
backend/
├── app/
│   ├── main.py                 FastAPI app, docs URLs, error handler, router registration
│   ├── seed.py                 Idempotent demo users, projects, milestones and deliverables
│   ├── seed_perf.py            Full-scale synthetic dataset for performance tests
│   ├── api/
│   │   ├── router.py           Composes /api/v1 routes
│   │   ├── deps.py             Reads session cookie and resolves current user
│   │   └── routes/
│   │       ├── health.py       /health/live and /health/ready
│   │       └── meta.py         /api/v1/meta
│   ├── core/
│   │   ├── config.py           Environment settings via pydantic-settings
│   │   ├── errors.py           AppError and uniform {"error": {...}} response
│   │   ├── http.py             Client IP extraction for audit
│   │   ├── logging.py          JSON logging configuration
│   │   ├── storage_report.py   Storage usage and discrepancy report
│   │   └── audit/
│   │       ├── models.py       Audit table
│   │       ├── service.py      record_audit and purge_audit_logs
│   │       └── purge.py        CLI for audit retention
│   ├── db/
│   │   ├── base.py             SQLAlchemy declarative base and naming convention
│   │   ├── session.py          Async engine, session factory and DB readiness check
│   │   ├── mixins.py           created_at / modified_at columns
│   │   ├── types.py            PostgreSQL enum helper
│   │   └── models.py           Imports all models so Alembic sees them
│   └── modules/
│       ├── auth/               Users, sessions, login/logout/me
│       ├── projects/           Projects, participants, milestones and project RBAC
│       ├── deliverables/       Deliverables, submissions, reviews, history and forum
│       ├── storage/            File metadata and local file storage
│       └── notifications/      Notification model only; no active endpoint/service
├── alembic/
│   ├── env.py                  Alembic configuration and metadata wiring
│   └── versions/               Migration scripts
├── tests/                      Backend pytest suite
├── Dockerfile                  Development and production targets
├── entrypoint.sh               Runs alembic upgrade head, then uvicorn
├── pyproject.toml              Ruff, Pyright and pytest configuration
├── requirements.txt            Runtime dependencies
└── requirements-dev.txt        Test/lint/type dependencies
```

### Backend modules

Each domain module follows the same pattern:

| File | Responsibility |
|---|---|
| `models.py` | SQLAlchemy tables and relationships. |
| `schemas.py` | Pydantic request/response models and API↔DB value mappings. |
| `router.py` | FastAPI endpoints and dependency wiring. |
| `service.py` | Business logic, state transitions and database operations. |
| `enums.py` | Domain enums. |
| `dependencies.py` | Access control and resource loading, when applicable. |
| `security.py` | Password/session helpers, currently in `auth/`. |

Specific responsibilities:

- `auth/`
  - `models.py`: `Usuario`, `Sesion`.
  - `security.py`: Argon2id password hashing, session token hashing, cookie handling.
  - `service.py`: credential validation, session creation/expiry/deletion.
  - `router.py`: `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`.

- `projects/`
  - `models.py`: `Proyecto`, `Participacion`, `Hito`, plus `Plantilla` and `ItemPlantilla` (models only, no active template flow).
  - `dependencies.py`: loads a project only for participants; manager-only guard.
  - `schemas.py`: project/milestone API shapes and DB↔API enum mappings.
  - `service.py`: project CRUD, participant resolution, milestone ordering, project detail/count calculations.
  - `router.py`: project list/create/detail/edit and milestone creation.

- `deliverables/`
  - `models.py`: `Entregable`, `Entrega`, `Revision`, `Comentario` (user messages and generated lifecycle events).
  - `dependencies.py`: milestone/deliverable/file access; manager and collaborator guards; resolves submission and review files.
  - `schemas.py`: deliverable, submission, review (including review files), forum and pending-review API shapes.
  - `service.py`: deliverable create/edit, upload validation (files, HTTPS link, or both), review file attachments, version numbering, review state machine, overdue calculation, history, forum timeline and pending reviews.
  - `router.py`: deliverable detail/edit, multipart reviews with files, submissions, forum, pending reviews and file download.

- `storage/`
  - `models.py`: `Archivo` metadata for files attached to a submission or a review.
  - `service.py`: `StorageBackend` protocol and `LocalStorage`.
  - `enums.py`: allowed file formats.

- `notifications/`
  - `models.py`: notification table/model.
  - No router, service or frontend flow yet.

### Backend tests

| File | Coverage |
|---|---|
| `tests/conftest.py` | Test database cleanup and `httpx` test client. |
| `tests/test_auth.py` | Login, cookies, logout, expiry, lockout and hashing. |
| `tests/test_projects.py` | Project creation/edit, participants, milestones and RBAC. |
| `tests/test_deliverables.py` | Deliverables, file/link submissions, reviews with files, history, overdue and forum events. |
| `tests/test_health.py` | Liveness/readiness endpoints. |
| `tests/test_meta.py` | Application metadata endpoint. |
| `tests/test_nfr_rbac.py` | OpenAPI inventory guard and role × endpoint RBAC matrix. |
| `tests/test_nfr_uploads.py` | Allowed formats/MIME matrix and atomic rejection. |
| `tests/test_nfr_schema.py` | Schema check for absence of RUT/grade columns. |
| `tests/test_nfr_observability.py` | Audit rows, JSON logs, IP extraction and retention purge. |
| `tests/test_nfr_storage.py` | Storage thresholds, discrepancy and directory-size checks. |
| `tests/nfr_helpers.py` | Shared fixtures/helpers for the NFR backend tests. |

### CI automation

| Command or file | Purpose |
|---|---|
| `scripts/ci/run-ci.sh` | Runs the PR, nightly or combined CI profile on a Linux host, using isolated Compose projects and writing `reports/ci/<timestamp>/`. |
| `scripts/ci/remote-ci.sh` | Syncs the working tree over SSH, invokes `run-ci.sh` remotely and fetches reports. |
| `scripts/cd/deploy-demo.sh` | Builds the demo stack, preserves `.env.demo`, seeds demo data, verifies demo login and enables HTTPS. |
| `scripts/cd/setup-nginx-tls.sh` | Starts the Nginx proxy, obtains/reuses the Let’s Encrypt certificate, verifies HTTPS locally and redirects HTTP to HTTPS. |
| `scripts/cd/renew-certificates.sh` | Renews the Let’s Encrypt certificate and reloads Nginx; supports `--dry-run`. |
| `scripts/cd/remote-deploy.sh` | Syncs the working tree over SSH and runs the demo deployment on the remote host. |
| `.github/workflows/ci.yml` | GitHub Actions PR CI and demo deploy job after CI on `main`. |
| `.github/workflows/nfr-nightly.yml` | GitHub Actions nightly NFR jobs. |

### NFR verification

| Command or file | Purpose |
|---|---|
| `scripts/nfr/coverage.sh` | Runs the backend suite with greenlet-aware coverage and the 80% gate; writes `reports/nfr/coverage/`. |
| `scripts/nfr/compose_smoke.sh` | Builds `db`, `backend` and `web`, waits for health, seeds, checks the SPA and logs in. |
| `scripts/nfr/e2e.sh` | Resets the isolated `hito_e2e` stack, seeds and runs Playwright. |
| `frontend/e2e/` | Playwright PA flows, axe scans, keyboard/focus and 360 px checks. |
| `compose.e2e.yaml` | E2E override: separate database, port `18080`, backend not exposed. |
| `scripts/nfr/tls_smoke.sh` | Generates self-signed certs and verifies TLS 1.2/1.3, HSTS, redirect and Secure cookies. |
| `scripts/nfr/tls_check.py` | Handshake, HTTPS, HSTS, redirect and static-config checks used by the TLS smoke test. |
| `scripts/nfr/generate_tls_certs.sh` | Generates the ignored `certs/localhost.crt` and key. |
| `scripts/nfr/storage_report.sh` | Runs the local storage/discrepancy report and writes `reports/nfr/storage.json`. |
| `scripts/nfr/backup.sh` | Dumps PostgreSQL, archives uploads and writes a manifest with hashes, sizes and counts. |
| `scripts/nfr/restore_drill.sh` | Verifies a backup, restores it into a throwaway database, compares counts/files and measures RPO/RTO. |
| `scripts/nfr/perf.sh` | Resets the `hito_perf` stack, seeds the SRS scale, runs load, navigation and memory reports. |
| `scripts/nfr/load_test.py` | Async API load test with p50/p95/p99, error rate and throughput. |
| `scripts/nfr/memory_sampler.py` | Samples `docker stats` for the perf server containers. |
| `scripts/nfr/memory_report.py` | Summarizes peak/mean RAM and suggests an AWS instance size. |
| `frontend/e2e/perf.spec.ts` | Playwright navigation and 10 MB upload timings. |
| `docs/operations/performance.md` | Load mix, reports, RAM sampling and AWS sizing procedure. |
| `docs/operations/tls.md` | Local TLS procedure and production Certbot/SSL Labs runbook. |
| `docs/operations/storage.md` | Storage quota/alert procedure and production S3/budget steps. |
| `docs/operations/backup-restore.md` | Backup, restore drill and production offsite/retention steps. |
| `docs/nfr/wcag-manual-checklist.md` | Manual WCAG 2.1 AA checklist for items axe cannot cover. |
| `docs/nfr/usability-protocol.md` | RNF-U-3 participant protocol, PA-1/PA-2/PA-5 scripts and pass criteria. |
| `docs/nfr/sus-form.md` | SUS questionnaire and scoring instructions. |
| `docs/nfr/results-template.md` | Per-session results, SUS, findings and action log. |
| `backend/tests/test_nfr_*.py` | Automated security, upload, schema and observability checks. |
| `.github/workflows/ci.yml` | Runs backend quality/tests/coverage, frontend checks and Docker smoke on GitHub. |

## Frontend

```text
frontend/
├── src/
│   ├── main.tsx                React root, QueryClient, BrowserRouter, CSS imports
│   ├── App.tsx                 Route table and session-expiry listener
│   ├── api/
│   │   ├── types.ts            TypeScript mirror of API request/response types
│   │   ├── client.ts           fetch wrapper, cookie credentials, ApiError, uploads
│   │   └── queries.ts          TanStack Query hooks, query keys and invalidation
│   ├── pages/                  One file per route/screen
│   ├── components/             Reusable UI and dialogs
│   ├── styles/
│   │   ├── tokens.css          Local fonts and CSS variables
│   │   ├── base.css            Layout, header, buttons, forms, auth
│   │   └── components.css      Cards, timeline, chips, forum, dialogs, uploads
│   ├── utils/format.ts         Date, name, role, format and type labels
│   └── test/                   Test setup, fixtures and helpers
├── e2e/                        Playwright PA flows, axe, keyboard and 360 px tests
├── playwright.config.ts        Chromium, Firefox and WebKit projects
├── public/fonts/               Local Poppins/Roboto fonts and licences
├── index.html                  Vite HTML entry point
├── package.json                Scripts and dependencies
├── vite.config.ts              Dev server and /api, /health proxy
├── vitest.config.ts            jsdom test configuration
├── tsconfig.json               Strict TypeScript configuration
├── eslint.config.js            ESLint rules
├── .prettierrc                 Formatting rules
├── Dockerfile                  Builds Vite app, serves with Nginx
├── nginx.conf                  SPA fallback and backend proxy
└── nginx.tls.conf              TLS profile with HSTS and HTTPS redirect
```

### Frontend pages

| File | Screen |
|---|---|
| `LoginPage.tsx` | `/login` login form. |
| `ProjectsPage.tsx` | `/` portfolio and pending-review inbox. |
| `ProjectDetailPage.tsx` | `/projects/:projectId` project timeline and manager actions. |
| `ProjectFormPage.tsx` | `/projects/new` and `/projects/:projectId/edit`. |
| `DeliverablePage.tsx` | `/deliverables/:deliverableId` detail, file/link upload, review with optional files and forum message, and forum timeline. |
| `SubmissionHistoryPage.tsx` | `/deliverables/:deliverableId/history` manager-only version history. |
| `NotFoundPage.tsx` | Fallback route. |

Tests are colocated as `*.test.tsx` in `src/pages/`.

E2E tests live in `frontend/e2e/` and run against the isolated `hito_e2e` stack. `npm run test:e2e` runs Playwright; use `./scripts/nfr/e2e.sh --project=chromium` for the CI-equivalent run.

### Frontend components

| File | Responsibility |
|---|---|
| `AppShell.tsx` | Authenticated header, navigation, account menu and logout. |
| `ProtectedRoute.tsx` | Redirects unauthenticated users to `/login`. |
| `Modal.tsx` | Native `<dialog>` wrapper. |
| `MilestoneDialog.tsx` | Create milestone. |
| `DeliverableDialog.tsx` | Create/edit deliverable. |
| `StatusChip.tsx` | Deliverable status plus separate overdue badge. |
| `ParticipantChips.tsx` | Participants and roles. |
| `ReviewBlock.tsx` | Review decision summary. |
| `SubmissionFiles.tsx` | File list and download links. |
| `LoadingState.tsx`, `ErrorState.tsx`, `EmptyState.tsx`, `Feedback.tsx` | Shared page states and action feedback. |

## Where to change what

| Change | Files to start with |
|---|---|
| Add/modify a backend endpoint | `backend/app/modules/<domain>/router.py`, `schemas.py`, `service.py` |
| Change access rules/RBAC | `backend/app/api/deps.py`, `projects/dependencies.py`, `deliverables/dependencies.py` |
| Add/change a database table or column | Module `models.py`, then `backend/app/db/models.py`, then a new Alembic migration |
| Change API JSON shape | Backend `schemas.py` + `frontend/src/api/types.ts` + `client.ts`/page using it |
| Change deliverable state rules, uploads, reviews or forum | `backend/app/modules/deliverables/service.py` and its tests |
| Change file storage/limits | `backend/app/modules/storage/service.py`, deliverable service, `frontend/nginx.conf`, `.env` |
| Change login/session behavior | `backend/app/modules/auth/`, `backend/app/api/deps.py`, `frontend/src/api/client.ts`, `frontend/src/App.tsx` |
| Add a new frontend screen | New file in `frontend/src/pages/` + route in `frontend/src/App.tsx` |
| Add a frontend API call | `frontend/src/api/types.ts` → `client.ts` → `queries.ts` |
| Change cache refresh after an action | `frontend/src/api/queries.ts` invalidation hooks |
| Change layout, forms, buttons or cards | `frontend/src/styles/base.css` / `components.css` |
| Change colors or fonts | `frontend/src/styles/tokens.css` and `frontend/public/fonts/` |
| Change demo users/projects/deliverables | `backend/app/seed.py` |
| Change performance dataset or load mix | `backend/app/seed_perf.py`, `scripts/nfr/load_test.py`, `docs/operations/performance.md` |
| Change runtime services, ports or volumes | `compose.yaml` |
| Change Nginx routing or upload size | `frontend/nginx.conf` |
| Change TLS or HTTPS behavior | `frontend/nginx.tls.conf`, `compose.tls.yaml`, `scripts/nfr/tls_check.py` |
| Change storage quotas or alerts | `backend/app/core/storage_report.py`, `scripts/nfr/storage_report.sh`, `docs/operations/storage.md` |
| Change backups or restore drills | `scripts/nfr/backup.sh`, `scripts/nfr/restore_drill.sh`, `docs/operations/backup-restore.md` |
| Change E2E flows or accessibility checks | `frontend/e2e/`, `frontend/playwright.config.ts`, `scripts/nfr/e2e.sh`, `compose.e2e.yaml` |
| Change the usability protocol or SUS | `docs/nfr/usability-protocol.md`, `docs/nfr/sus-form.md`, `docs/nfr/results-template.md` |
| Change backend test setup | `backend/tests/conftest.py` |
| Change or add NFR checks | `backend/tests/test_nfr_*.py`, `scripts/nfr/` |
| Change coverage configuration or gate | `backend/pyproject.toml`, `scripts/nfr/coverage.sh` |
| Change audit or structured logging | `backend/app/core/audit/`, `backend/app/core/logging.py`, `backend/app/core/http.py` and the affected routers |
| Change CI | `.github/workflows/ci.yml`, `.github/workflows/nfr-nightly.yml` |
| Change remote CI behavior | `scripts/ci/run-ci.sh`, `scripts/ci/remote-ci.sh`, `README.md` |
| Change demo deployment | `compose.demo.yaml`, `compose.proxy.yaml`, `deploy/nginx/`, `scripts/cd/deploy-demo.sh`, `scripts/cd/setup-nginx-tls.sh`, `scripts/cd/renew-certificates.sh`, `scripts/cd/remote-deploy.sh`, `.github/workflows/ci.yml` |
| Change frontend test helpers/fixtures | `frontend/src/test/helpers.tsx`, `fixtures.ts` |
| Change requirements/specification | `spec/hito-must-build-spec.md`; `spec/main.tex`; `spec/nfr-test-plan.md`; `spec/main-tex-nfr-changes.md` |

## Important gotchas

- `backend/app/modules/projects/models.py` contains `Plantilla` and `ItemPlantilla`, and `notifications/` contains a model only. Do not assume their features are implemented. `core/audit/` is wired to critical actions.
- `reports/` contains generated coverage and smoke artifacts; it is ignored by Git. Upload it as a CI artifact instead of committing it.
- The remote runner uses Compose project `hito_ci`; do not set it to `hito`, which is the production project. The smoke and coverage scripts can run `down -v` on their project.
- The demo deploy uses Compose project `hito` on loopback port `9080`, plus the `hito_proxy` Nginx/Certbot stack on ports `80`/`443`. It preserves `.env.demo` and never runs `down -v`; the demo password is the synthetic seed password, so it is only for demonstrations.
- `certs/` contains generated self-signed certificates and is ignored by Git. The public demo uses Nginx/Certbot with Let’s Encrypt in `compose.proxy.yaml`; SSL Labs remains pending. See `docs/operations/tls.md`.
- `storage_report.py` measures the local uploads volume and `archivo.tamano`; it does not replace S3 lifecycle, CloudWatch alarms or AWS Budgets. See `docs/operations/storage.md`.
- `backups/` contains database/uploads copies with personal and academic data; it is ignored by Git. Offsite storage and encryption remain pending for production. See `docs/operations/backup-restore.md`.
- The E2E stack (`compose.e2e.yaml`) is independent (`hito_e2e`, port `18080`) and resets its database. It does not touch development data. Playwright browsers need `npx playwright install --with-deps`; WebKit requires system libraries that CI installs.
- The performance stack (`compose.perf.yaml`) is independent (`hito_perf`, port `18081`). `seed_perf.py` refuses to run unless `APP_ENV=perf` and the database name contains `perf`. It creates sparse upload files; do not confuse apparent size with host disk usage. RAM samples exclude the load-generator container.
- `MilestoneStatus` exists in the database model, but the current frontend does not implement milestone completion/status actions.
- Forum `Comentario` rows have `tipo = usuario | sistema`; system lifecycle events have `autor_id = NULL` and are rendered differently from user messages.
- `archivo` rows belong to exactly one of `entrega` or `revision`. Review files are not submission versions and are only attached when the review is registered.
- Database and domain values are Spanish (`memoria`, `gestor`, `entregado`, etc.); API values are English (`memoir`, `manager`, `submitted`, etc.). Check `projects/schemas.py` and `deliverables/schemas.py` before changing payloads.
- The Docker `web` service serves the compiled `frontend/dist`; rebuild it after frontend changes. The Vite dev server on port `5173` proxies to the backend on `8000`.
- `backend-test` uses the `hito_test` database created by `db/init/01-create-test-db.sql`.
- `deprecated-mockup/` is reference material only. Its fonts were copied into `frontend/public/fonts/`.
- `frontend/dist/`, `node_modules/`, pytest/Ruff caches and `.env` are generated/local and ignored.

## Useful reading order

1. Backend: `app/main.py` → `api/router.py` → module `router.py` → `service.py` → `models.py`/`schemas.py`.
2. Frontend: `main.tsx` → `App.tsx` → target page → `api/queries.ts` → `api/client.ts` → `api/types.ts`.
