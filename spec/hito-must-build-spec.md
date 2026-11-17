# Hito — Must-RF build specification

**Version:** 1.3
**Date:** 2026-11-16
**Source SRS:** `main.tex` (§1.3, §2.1–2.7, §3, §4, §5, §6, §9.1, §10, §11)
**Purpose:** single, concise build reference for implementing the Must functional requirements of *Hito* and leaving the non-functional requirements ready for a later phase.

> This build specification is maintained alongside `main.tex`. The SRS is the requirements source; this document records implementation decisions, contracts and schema details. `main.tex` and `deprecated-mockup/` are not modified without a separate, explicit instruction.

---

## 1. Scope

### 1.1 Requirements implemented now

The implementation covers the 12 original Must RFs **plus RF-11, promoted to Must by the user**:

| ID | Title | Priority |
|---|---|---|
| RF-1 | Inicio de sesión | Must |
| RF-2 | Visualización de proyectos | Must |
| RF-3 | Detalle de un proyecto | Must |
| RF-4 | Creación de proyectos | Must |
| RF-5 | Edición de la información del proyecto | Must |
| RF-6 | Creación de hitos | Must |
| RF-8 | Creación de entregables | Must |
| RF-9 | Edición de entregables | Must |
| RF-10 | Subida de archivos | Must |
| RF-11 | Comentarios de una entrega (foro) | **Must (promoted)** |
| RF-12 | Registro de entregas previas | Must |
| RF-13 | Estado de un entregable | Must |
| RF-14 | Modificación de estado de entregable | Must |

The following Must acceptance flows are the final target:

- **PA-1** — create a project with two milestones, one deliverable and one collaborator; the collaborator sees it after login.
- **PA-2** — collaborator submits v1, manager requests changes and comments in the forum, collaborator submits v2, manager approves; both versions and their reviews are preserved.
- **PA-3** — an expired deliverable shows “Atrasado”; a late submission is accepted with its real timestamp and the badge remains until approval.
- **PA-4** — a student cannot open a project in which they do not participate.

### 1.2 Explicitly out of scope now

Do not implement the following. Design migrations and interfaces so they can be added later without rewriting the domain:

- RF-7 (edit milestone name), RF-15 (milestone templates), RF-16 (kanban), RF-17 (email notifications), RF-18 (calendar export), RF-19 (invitations/activation), RF-20 (milestone completion), RF-21 (data-subject rights).
- All RNF acceptance work: load/stress tests, back-ups, TLS provisioning, uptime monitoring, WCAG audit, browser matrix, coverage threshold, audit log, centralized logging, SUS/usability study.
- Email, password reset, open registration, OAuth/social login, account settings, account deletion.
- Any modification to `deprecated-mockup/`. Its `AGENTS.md` governs only that deprecated static mockup; the new application lives outside that directory and follows the ALT-1 decision.
- Kanban, calendar export, templates, notification centre, student directory, institutional integrations.
- Deleting projects, milestones, deliverables, submissions, reviews or forum messages.
- Project-level activity feeds. Automatic forum events are limited to each deliverable's lifecycle.
- File preview, plagiarism detection, document editing.

### 1.3 Resolved decisions

These decisions override or clarify the SRS text and are binding for the build:

1. **RF-11 is Must** for this implementation. The SRS still lists it as Should; update `main.tex` later (§14).
2. **Review comments do not exist as a review field.** A review records only the decision (`Aprobado` / `Cambios solicitados`). Comments are forum messages on the deliverable. The manager flow is: review → register decision → optionally leave a forum comment. PA-2 is satisfied by the forum comment.
3. **Deliverables have no manual position field.** RF-8's “posición” means the deliverable is placed under the corresponding milestone. Within a milestone, deliverables are ordered by `deadline_at` ascending (tie-breaker: `created_at`, then `id`; DB columns `fecha_limite`, then `created_at`). Milestones do have a manual position (`orden` in the DB, `order_index` in the API/JSON) because RF-6 requires a position in the milestone list.
4. **RB-6 editing rule:** when editing a deliverable, reject only a *changed* deadline that is in the past. If the existing deadline is already past and the manager edits other fields without changing it, the save is allowed.
5. **Re-upload while `Entregado` is allowed.** A new immutable version is created; the deliverable remains `Entregado` (self-transition), and the manager reviews the latest version. `Aprobado` is terminal.
6. **Files or HTTPS link.** Every submission must contain at least one valid file, a valid `https://` link, or both. Files and the link are alternative delivery methods, not mutually exclusive.
7. **Accounts are seeded only.** No registration, no invitation flow, no account creation UI. Participant emails must match an existing active seeded account; unknown emails are rejected with a clear message.
8. **UI reuses the deprecated mockup's visual identity** (palette, fonts, spacing, component language), but not its static HTML/JS or its demo scaffolding.
9. **Three project types** per SRS §5.1: `Memoria de título`, `Tesis`, `Proyecto de investigación`. The mockup's separate “Tesis de magíster/doctorado” options are not adopted.
10. **No project templates.** A new project starts with no milestones.
11. **No project closing UI.** `status` defaults to `active`; `closed` is reserved for later.
12. **No milestone completion state.** Project detail may show derived progress (`X de Y entregables aprobados`), but no automatic/manual completion action.
13. **Forum lifecycle events.** The deliverable forum includes automatic, read-only system entries for the deliverable's lifecycle: creation, edition, submission and review. They are distinct from user comments and from review decisions: they have no author and are rendered as gray timeline items. Reviews still record only the decision.
14. **Review attachments.** A manager may attach optional, multiple files while registering a review. Files use the deliverable's allowed formats and maximum size. They belong to the review, not to a new submission version, and cannot be added after the review is registered. Review decisions remain decision-only; files are not comments. Collaborators may download files attached to the latest review.

---

## 2. Product and architecture

### 2.1 Architecture

Use **ALT-1** from SRS §8:

- **Frontend:** React + TypeScript + Vite, single-page app.
- **Backend:** FastAPI REST API, Python 3.13 runtime in Docker.
- **Database:** PostgreSQL 18.
- **Deployment:** Docker Compose; Nginx serves the SPA and proxies `/api` and `/health` to FastAPI.
- **Auth:** own email/password login; opaque server-side sessions in an HttpOnly cookie. No OAuth, no open sign-up.
- **File storage:** local private volume behind a small storage abstraction; S3 can replace the local adapter later.
- **Tests:** pytest + httpx against PostgreSQL; Vitest + React Testing Library on the frontend.

```text
Browser
  │ HTTPS/HTTP
  ▼
Nginx (web) ── static React build
  │ /api, /health
  ▼
FastAPI (backend) ── PostgreSQL
  │
  └── private uploads volume
```

### 2.2 Repository layout

Create new top-level directories; leave `deprecated-mockup/` untouched.

```text
backend/
  app/
    main.py
    core/
      config.py
      errors.py
      logging.py
      audit/          # registro_auditoria (cross-cutting)
    db/
      base.py
      mixins.py
      session.py
      types.py
      models.py       # imports every model for Alembic
    modules/
      auth/           # usuario, sesion; login/sessions/RBAC later
      projects/       # proyecto, participacion, plantilla,
                      # item_plantilla, hito
      deliverables/   # entregable, entrega, revision, comentario
      storage/        # archivo, FileFormat; local/S3 later
      notifications/  # notificacion; email later
    api/
      router.py
      routes/
        health.py
        meta.py
  alembic/
  tests/
  requirements.txt
  requirements-dev.txt
  pyproject.toml     # ruff, pyright, pytest config
  Dockerfile
frontend/
  src/
    main.tsx
    App.tsx
    api/             # client, types, query hooks
    components/
    pages/
    styles/          # tokens, base, components, pages
    test/
  public/fonts/      # Poppins/Roboto + OFL licences
  package.json
  tsconfig.json
  vite.config.ts
  vitest.config.ts
  Dockerfile
  nginx.conf
compose.yaml
.env.example
.gitignore
README.md
```

The backend structure follows the five components of `ComponentC4.svg`:

| Module | Owns | C4 component |
|---|---|---|
| `modules/auth` | `usuario`, `sesion` | Servicio de Autenticación |
| `modules/projects` | `proyecto`, `participacion`, `plantilla`, `item_plantilla`, `hito` | Servicio de Proyectos |
| `modules/deliverables` | `entregable`, `entrega`, `revision`, `comentario` | Servicio de Entregables |
| `modules/storage` | `archivo` | Servicio de Almacenamiento |
| `modules/notifications` | `notificacion` | Servicio de Notificaciones |

`registro_auditoria` lives under `core/audit` as a cross-cutting concern, not as a sixth business module. In step 1 only the packages and models exist; routers and services are added with each feature.

### 2.3 Dependency set

Backend runtime:

- `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`
- `pydantic`, `pydantic-settings`, `email-validator`, `python-multipart`
- `pwdlib[argon2]` (Argon2id password hashing)
- `aiofiles` (streaming uploads)

Backend development:

- `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx`, `ruff`, `pyright`

Frontend runtime:

- `react`, `react-dom`, `react-router-dom`
- `@tanstack/react-query`
- `react-hook-form`, `@hookform/resolvers`, `zod`

Frontend development:

- `typescript`, `vite`, `@vitejs/plugin-react`, `@types/react`, `@types/react-dom`, `@types/node`
- `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`
- `eslint`, `@eslint/js`, `typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `prettier`

No CSS framework, icon library, component library or external font CDN. Icons are inline SVG, matching the mockup's approach.

### 2.4 Docker Compose services

`compose.yaml` defines:

| Service | Purpose |
|---|---|
| `db` | PostgreSQL 18 Alpine, named volume, healthcheck. Its init script creates `hito` and `hito_test`. |
| `backend` | FastAPI production target; depends on `db` healthy; runs `alembic upgrade head` then Uvicorn; mounts the private uploads volume; healthcheck on `/health/live`. |
| `web` | Multi-stage frontend build served by Nginx on host port `8080`; proxies `/api` and `/health` to `backend`; SPA fallback to `index.html`. |
| `backend-test` | Profile `test`; development target with backend dev dependencies; uses `hito_test`; command is overridden to `pytest`/`ruff`/`pyright`. |

Frontend checks run on the host with Node 22 (`npm ci && npm run lint && npm run typecheck && npm run test -- --run && npm run build`) or in an equivalent CI job later.

### 2.5 Coding conventions

- Backend: Python 3.13, `ruff` line length 88, double quotes, `pyright` strict, type hints on public functions, `async def` endpoints, FastAPI `Depends`, Pydantic v2 with `extra="forbid"` and `from_attributes=True`, stdlib `logging`.
- Frontend: TypeScript strict plus `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride` and `verbatimModuleSyntax`; `type` only (no `interface`); string-literal unions; `any` banned; named exports; ESLint + Prettier with semicolons, single quotes, trailing commas, 4 spaces, 100 columns.
- File names: `kebab-case` for non-component modules, `PascalCase.tsx` for components.
- Code identifiers in English; UI text and code comments/public API docs in Spanish.
- Persistence: SRS Spanish table/column names and DB enum values; API/JSON field names and enum values English. Map explicitly in the repository/Pydantic layer. `created_at` and `modified_at` are the technical audit columns on every table.

---

## 3. Domain model

### 3.1 Enumerations (Spanish DB values, English API/JSON values)

The relational schema uses the SRS's Spanish table/column names and Spanish enum values. The REST API and JSON use the English values below; the repository/Pydantic serialization layer maps between them.

| Enum | DB values | API/JSON values | UI labels |
|---|---|---|---|
| `UserType` | `profesor`, `estudiante` | `professor`, `student` | Profesor, Estudiante |
| `UserStatus` | `invitada`, `activa` | `invited`, `active` | Invitada, Activa |
| `ProjectType` | `memoria`, `tesis`, `investigacion` | `memoir`, `thesis`, `research` | Memoria de título, Tesis, Proyecto de investigación |
| `ProjectStatus` | `activo`, `cerrado` | `active`, `closed` | Activo, Cerrado |
| `ParticipantRole` | `gestor`, `colaborador` | `manager`, `collaborator` | Gestor, Colaborador |
| `MilestoneStatus` | `pendiente`, `en_curso`, `completado` | `pending`, `in_progress`, `completed` | Pendiente, En curso, Completado |
| `DeliverableStatus` | `pendiente`, `entregado`, `cambios_solicitados`, `aprobado` | `pending`, `submitted`, `changes_requested`, `approved` | Pendiente, Entregado, Cambios solicitados, Aprobado |
| `ReviewDecision` | `aprobado`, `cambios_solicitados` | `approved`, `changes_requested` | Aprobado, Cambios solicitados |
| `FileFormat` | `pdf`, `zip`, `docx` | `pdf`, `zip`, `docx` | PDF, ZIP, DOCX |

“Atrasado” is **not** a status. It is a computed boolean (`is_overdue`) displayed as a badge next to the status.

### 3.2 Relational schema (SRS-aligned)

Use UUID primary keys (`uuid.uuid4` or PostgreSQL `gen_random_uuid()`), Spanish `snake_case` table/column names from §5.1/Annex G.2, and timezone-aware UTC timestamps. The API/JSON field names and enum values remain English (§3.1); map them in the repository/Pydantic layer.

Every table has the technical audit columns `created_at` and `modified_at` (`timestamptz`, not null, default `now()`). `modified_at` is updated on every row update; immutable rows (`entrega`, `archivo`, `revision`, `comentario`, `registro_auditoria`) keep `modified_at = created_at`. The SRS business timestamps (`fecha_creacion`, `fecha_alta`, `fecha_ultima_modificacion`, `fecha_envio`, `fecha`, etc.) remain as separate columns; services set the business timestamp and the generic audit timestamp from the same event when they represent the same moment.

Items marked `[later]` are part of the SRS target model but are not used by the Must flows; they can be created now or in a subsequent migration. `sesion` is implementation-only and does not appear in §5.1/Annex G.2.

#### `usuario`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `nombre` | text | not null, 1–200 chars |
| `correo` | text | not null, unique, lowercase, valid email |
| `tipo` | enum `UserType` | not null |
| `credencial` | text | not null; Argon2id hash in this phase |
| `estado` | enum `UserStatus` | not null, default `invitada`; seeded demo users are `activa` (invitation flow later: RF-19) |
| `consentimiento_fecha` | timestamptz | nullable (data-rights flow later: RF-21) |
| `consentimiento_version` | text | nullable (data-rights flow later: RF-21) |
| `fecha_creacion` | timestamptz | not null, default now |
| `created_at` | timestamptz | not null, default now |
| `modified_at` | timestamptz | not null, default now |

No RUT, phone, address, birth date, grades or sensitive data. The `estado` and consent columns support the deferred RF-19/RF-21 flows.

#### `sesion` (implementation-only)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `usuario_id` | UUID | FK `usuario.id`, not null, cascade |
| `token_hash` | text | not null, unique; SHA-256 of the opaque cookie token |
| `fecha_expiracion` | timestamptz | not null |
| `created_at` | timestamptz | not null, default now |
| `modified_at` | timestamptz | not null, default now |

Unique `token_hash`; index `(usuario_id)`.

#### `proyecto`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `tipo` | enum `ProjectType` | not null |
| `tema` | text | not null, 1–300 chars |
| `estado` | enum `ProjectStatus` | not null, default `activo` |
| `fecha_inicio` | date | not null, default current date |
| `fecha_cierre` | date | nullable `[later: project closing]` |
| `fecha_ultima_modificacion` | timestamptz | not null, default now, indexed |
| `created_at` | timestamptz | not null, default now |
| `modified_at` | timestamptz | not null, default now, indexed |

The creator is recorded as a `gestor` in `participacion`; no separate `creado_por_id` column is needed.

#### `participacion`

| Column | Type | Constraints |
|---|---|---|
| `usuario_id` | UUID | FK `usuario.id`, cascade, PK part |
| `proyecto_id` | UUID | FK `proyecto.id`, cascade, PK part |
| `rol` | enum `ParticipantRole` | not null |
| `fecha_alta` | timestamptz | not null, default now |
| `created_at` | timestamptz | not null, default now |
| `modified_at` | timestamptz | not null, default now |

PK `(usuario_id, proyecto_id)` enforces one role per user per project. Add indexes on `usuario_id` and `proyecto_id`.

#### `plantilla` `[later: RF-15]`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `nombre` | text | not null, 1–200 chars |
| `tipo_proyecto` | enum `ProjectType` | not null |
| `carrera` | text | not null, 1–200 chars |
| `created_at` | timestamptz | not null, default now |
| `modified_at` | timestamptz | not null, default now |

#### `item_plantilla` `[later: RF-15]`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `plantilla_id` | UUID | FK `plantilla.id`, cascade |
| `orden` | integer | not null, > 0 |
| `nombre` | text | not null, 1–200 chars |
| `created_at` | timestamptz | not null, default now |
| `modified_at` | timestamptz | not null, default now |

Unique `(plantilla_id, orden)`.

#### `hito`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `proyecto_id` | UUID | FK `proyecto.id`, cascade |
| `nombre` | text | not null, 1–200 chars |
| `orden` | integer | not null, > 0 |
| `estado` | enum `MilestoneStatus` | not null, default `pendiente` (completion flow later: RF-20) |
| `fecha_completado` | timestamptz | nullable (completion flow later: RF-20) |
| `created_at` | timestamptz | not null, default now |
| `modified_at` | timestamptz | not null, default now |

Unique `(proyecto_id, orden)`; index `(proyecto_id, orden)`.

#### `entregable`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `hito_id` | UUID | FK `hito.id`, cascade |
| `titulo` | text | not null, 1–200 chars |
| `descripcion` | text | not null, 1–4000 chars |
| `fecha_limite` | timestamptz | not null; refined from the ER's `date` for exact deadline instants |
| `formatos_admitidos` | jsonb | not null; non-empty list of `FileFormat` values |
| `tamano_max_mb` | integer | not null, default 50, range 1–200 |
| `estado` | enum `DeliverableStatus` | not null, default `pendiente` |
| `created_at` | timestamptz | not null, default now |
| `modified_at` | timestamptz | not null, default now |

Index `(hito_id, fecha_limite, created_at)`; this supports the RF-3 deadline ordering and the `created_at` tie-breaker.

#### `entrega`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `entregable_id` | UUID | FK `entregable.id`, cascade |
| `version` | integer | not null, > 0 |
| `autor_id` | UUID | FK `usuario.id`, not null |
| `fecha_envio` | timestamptz | not null, default now |
| `enlace` | text | nullable; HTTPS only; max 2048 |
| `created_at` | timestamptz | not null, default now |
| `modified_at` | timestamptz | not null, default now |

Unique `(entregable_id, version)`; index `(entregable_id, version)`.

#### `archivo`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `entrega_id` | UUID | FK `entrega.id`, cascade, nullable |
| `revision_id` | UUID | FK `revision.id`, cascade, nullable |
| `nombre` | text | not null, 1–255 chars; original filename |
| `tipo_mime` | text | not null |
| `tamano` | bigint | not null, > 0 |
| `clave_almacenamiento` | text | not null, unique |
| `sha256` | char(64) | not null |
| `created_at` | timestamptz | not null, default now |
| `modified_at` | timestamptz | not null, default now |

Check constraint `num_nonnulls(entrega_id, revision_id) = 1`: a file belongs to exactly one submission or one review. Index `(revision_id)`.

#### `revision`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `entrega_id` | UUID | FK `entrega.id`, cascade, **unique** |
| `gestor_id` | UUID | FK `usuario.id`, not null |
| `decision` | enum `ReviewDecision` | not null |
| `fecha` | timestamptz | not null, default now |
| `created_at` | timestamptz | not null, default now |
| `modified_at` | timestamptz | not null, default now |

Unique `entrega_id` enforces at most one review per delivery. **No `comentario` column:** reviews record only the decision; forum messages live in `comentario`. Although current §5.1 still lists `Revisión.comentario`, this build follows the newer decision and §14 records the SRS update. A review has 0–N rows in `archivo` through `revision_id`.

#### `comentario`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `entregable_id` | UUID | FK `entregable.id`, cascade |
| `autor_id` | UUID | FK `usuario.id`, nullable |
| `tipo` | enum `ForumMessageType` | not null, default `usuario` |
| `texto` | text | not null, 1–2000 chars after trim |
| `fecha` | timestamptz | not null, default now |
| `created_at` | timestamptz | not null, default now |
| `modified_at` | timestamptz | not null, default now |

`ForumMessageType` values: `usuario`, `sistema`. Check constraint: user messages require `autor_id`; system messages require `autor_id IS NULL`. Index `(entregable_id, fecha)`.

#### `notificacion` `[later: RF-17]`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `destinatario_id` | UUID | FK `usuario.id`, not null |
| `tipo_evento` | text | not null |
| `referencia_entidad` | text | not null |
| `fecha_envio` | timestamptz | not null |
| `created_at` | timestamptz | not null, default now |
| `modified_at` | timestamptz | not null, default now |

Index `(destinatario_id, fecha_envio)`.

#### `registro_auditoria` `[later: RNF-M-2]`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `usuario_id` | UUID | FK `usuario.id`, not null |
| `accion` | text | not null |
| `entidad` | text | not null |
| `entidad_id` | text | not null |
| `fecha` | timestamptz | not null |
| `ip` | text | not null; removed after 90 days |
| `created_at` | timestamptz | not null, default now |
| `modified_at` | timestamptz | not null, default now |

Index `(usuario_id, fecha)`.

Relationship summary from §5.1/Annex G.2:

- `usuario` 1–N `participacion`, `entrega`, `revision`, `comentario`, `notificacion`, `registro_auditoria`.
- `proyecto` 1–N `participacion`, `hito`.
- `hito` 1–N `entregable`.
- `entregable` 1–N `entrega`, `comentario`.
- `entrega` 1–N `archivo`; 1–0..1 `revision`.
- `revision` 1–N `archivo`; each file belongs to exactly one submission or one review.
- `plantilla` 1–N `item_plantilla`; a template is copied to `hito` when creating a project (RF-15, later).

### 3.3 Invariants

Role and status names in this section are the English API/domain values; the DB enum values are the Spanish equivalents in §3.1.

- A project always has at least one `manager` and at least one `collaborator`. Enforce in the service layer inside the same transaction; test both create and edit.
- A user has exactly one role per project, but may have different roles in different projects. User type (professor/student) is independent of project role: a student may be a manager and a professor may be a collaborator.
- The creator of a project is always a manager at creation.
- Every project-scoped mutation (project edit, milestone creation, deliverable creation/edit, submission, review or forum message) updates `proyecto.fecha_ultima_modificacion` and the technical `proyecto.modified_at` in the same transaction. This drives RF-2 ordering.
- Only a `professor` may create a project.
- Any manager (professor or student) may edit the project, milestones and deliverables.
- Only a `collaborator` may submit files, links, or both.
- Only a `manager` may review, create milestones/deliverables and edit deliverables.
- A submission is immutable. A correction is a new version.
- A review is immutable. One submission has at most one review.
- `approved` is terminal.
- Forum user messages and system events are append-only; no edit/delete.
- Project-level access is limited to participants. Non-participants receive `404` for project/deliverable resources.

### 3.4 State machine

```text
                 submit (v1..vn)
   pending ───────────────────────▶ submitted
      ▲                                  │
      │                                  ├── review: approved ──▶ approved (terminal)
      │                                  │
      │                                  └── review: changes ──▶ changes_requested
      │                                                                  │
      └──────────────────────────────────────────────────────────────────┘
                         submit (new version) ──▶ submitted
```

Values below are the English API/domain values; the DB values are the Spanish equivalents in §3.1.

Rules:

- Create deliverable → `pending`.
- Submit allowed from `pending`, `submitted` and `changes_requested`. `submitted` → `submitted` is the allowed re-upload self-transition.
- Submit forbidden from `approved` (409).
- Review allowed only when:
  - the actor is a manager of the project;
  - `deliverable.status == submitted`;
  - there is at least one submission;
  - the latest submission has no review.
- `approved` decision → `approved`; `changes_requested` → `changes_requested`.
- No other transitions.

### 3.5 Overdue calculation

Do not store “Atrasado”. Compute it. `deadline_at`, `status` and `submitted_at` below are API/domain names; the DB columns are `fecha_limite`, `estado` and `fecha_envio`.

```python
def is_overdue(deadline_at, status, submissions, now):
    if status == approved:
        return False
    if now <= deadline_at:
        return False
    return not any(s.submitted_at <= deadline_at for s in submissions)
```

- A submission exactly at the deadline counts as on time (`<=`).
- A late submission changes the status to `submitted` but keeps `is_overdue = True` until approval.
- An on-time submission followed by `changes_requested` is not overdue (there exists a submission before the deadline).
- Use UTC for comparisons. Display dates in `America/Santiago`.

---

## 4. API contract

Base path: `/api/v1`. JSON uses `snake_case`. IDs are UUID strings. Timestamps are ISO 8601 UTC (`Z`). All authenticated endpoints require the session cookie. The frontend and API share an origin in Docker and through the Vite dev proxy. API/JSON field names and enum values are English; the relational schema is Spanish (§3.2) and the repository layer maps between them.

### 4.1 Authentication

| Method | Path | Auth | Body | Response |
|---|---|---|---|---|
| `POST` | `/auth/login` | public | `{"email": str, "password": str}` | `200 {"user": User}` + `Set-Cookie` |
| `POST` | `/auth/logout` | session | — | `204`, clears cookie |
| `GET` | `/auth/me` | session | — | `200 {"user": User}` |

- Session token: 32 random bytes, URL-safe; store only its SHA-256 hash.
- Cookie: `hito_session`, `HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` when configured for production, max-age 8 hours.
- On login: reject blank fields with `422` message “Correo y/o contraseña vacíos.”; reject invalid credentials with `401` message “Correo o contraseña incorrectos.”; use the same generic error for unknown accounts.
- The account must have `usuario.estado = 'activa'` (API/JSON `active`). Unknown or non-active accounts receive the generic invalid-credentials response.
- New session on every login. Delete expired sessions opportunistically.
- CSRF baseline: `SameSite=Lax` plus an origin/referer allow-list check for unsafe methods when an `Origin` header is present.
- No sign-up, password-reset or OAuth endpoints.

### 4.2 Projects

| Method | Path | Role | Purpose |
|---|---|---|---|
| `GET` | `/projects` | authenticated participant | List the user's projects, sorted by `last_modified_at` descending |
| `POST` | `/projects` | professor | Create a project; creator becomes manager |
| `GET` | `/projects/{project_id}` | participant | Full detail: participants, milestones, deliverables |
| `PATCH` | `/projects/{project_id}` | manager | Edit topic, type and participants |
| `POST` | `/projects/{project_id}/milestones` | manager | Create a milestone |
| `POST` | `/milestones/{milestone_id}/deliverables` | manager | Create a deliverable |
| `PATCH` | `/deliverables/{deliverable_id}` | manager | Edit a deliverable |
| `GET` | `/deliverables/{deliverable_id}` | participant | Deliverable detail, latest submission, review, forum |
| `GET` | `/deliverables/{deliverable_id}/submissions` | manager | Full version history |
| `POST` | `/deliverables/{deliverable_id}/submissions` | collaborator | Upload a new version (multipart) |
| `POST` | `/deliverables/{deliverable_id}/reviews` | manager | Register decision on latest submission |
| `POST` | `/deliverables/{deliverable_id}/messages` | participant | Post a forum message |
| `GET` | `/reviews/pending` | manager | Deliverables awaiting the user's review |
| `GET` | `/files/{file_id}/download` | participant with access | Download a file |

No delete endpoints.

#### Create project request

```json
{
  "topic": "Reconocimiento de gestos para interfaces sin contacto",
  "project_type": "memoir",
  "manager_emails": ["co-guia@udec.cl"],
  "collaborator_emails": ["estudiante@udec.cl"]
}
```

- `manager_emails` optional; the authenticated professor is always added as manager.
- `collaborator_emails` at least one.
- Each email must be an existing account. Unknown email → `422` “No existe una cuenta activa con ese correo: {email}.”
- Duplicate across manager/collaborator lists → `422` “Un usuario no puede tener dos roles en el mismo proyecto.”
- Deduplicate and lowercase emails.
- `started_on` defaults to the current date; not required in the request.
- Creator becoming manager is non-negotiable.

#### Edit project request

Same participant fields, plus `topic` and `project_type`. The service replaces the participant set. It must reject:

- zero collaborators → `422` “El proyecto requiere tener al menos un colaborador.”
- zero managers → `422` “El proyecto requiere tener al menos un gestor.”
- an email with no active account.
- duplicates/conflicting roles.

A manager may remove themselves if another manager remains; the next request from that user will be treated as a non-participant.

#### Project list item

```json
{
  "id": "uuid",
  "topic": "…",
  "project_type": "memoir",
  "status": "active",
  "started_on": "2026-08-03",
  "last_modified_at": "2026-11-16T12:00:00Z",
  "my_role": "manager",
  "participants": [{"id": "uuid", "name": "…", "role": "manager"}],
  "total_deliverables": 8,
  "approved_deliverables": 2,
  "overdue_deliverables": 1,
  "pending_review_deliverables": 2,
  "next_deadline_at": "2026-11-20T23:59:00Z"
}
```

`next_deadline_at` is the earliest deadline among non-approved deliverables (`null` if none). All counts are derived, not stored.

#### Project detail

```json
{
  "id": "uuid",
  "topic": "…",
  "project_type": "memoir",
  "status": "active",
  "started_on": "2026-08-03",
  "last_modified_at": "2026-11-16T12:00:00Z",
  "my_role": "manager",
  "participants": [{"id": "uuid", "name": "…", "email": "…", "role": "manager"}],
  "milestones": [
    {
      "id": "uuid",
      "name": "Desarrollo y validación",
      "order_index": 2,
      "deliverables": [
        {
          "id": "uuid",
          "title": "Informe de avance 1",
          "deadline_at": "2026-11-20T23:59:00Z",
          "status": "submitted",
          "is_overdue": false,
          "latest_submission": {
            "version": 2,
            "submitted_at": "2026-11-15T21:14:00Z",
            "author_name": "…"
          },
          "review": null
        }
      ]
    }
  ]
}
```

- Milestones sorted by `order_index` ascending.
- Deliverables sorted by `deadline_at` ascending, then `created_at`, then `id`.
- `latest_submission` is `null` when there are no submissions.
- `review` is the review of the latest submission, or `null`.

#### Create milestone request

```json
{"name": "Propuesta de memoria", "position": 1}
```

- `name` non-empty; otherwise `422` “El Hito debe tener un nombre.”
- `position` integer in `1..(N+1)`. Lock the project row, shift existing `order_index >= position` by +1, insert. Use a deferrable unique constraint or carefully ordered updates.
- Default position = `N+1` (append) if omitted.

#### Create/edit deliverable request

```json
{
  "title": "Informe de avance 1",
  "description": "Informe con el estado del trabajo…",
  "deadline_at": "2026-11-20T23:59:00-03:00",
  "allowed_formats": ["pdf", "zip"],
  "max_file_size_mb": 50
}
```

- All fields required. Blank title/description or empty formats → `422` “Los campos no pueden estar vacíos.”
- `deadline_at` must be timezone-aware. On create: must be after `now`. On edit: if the submitted deadline differs from the stored deadline and is not after `now`, return `422` “Ingrese una fecha de entrega válida.” If unchanged, allow even if past.
- `allowed_formats` non-empty subset of `pdf`, `zip`, `docx`.
- `max_file_size_mb` integer 1–200, default 50.
- No manual position field.
- Edit cannot move a deliverable to another milestone.

#### Submission request

`POST /deliverables/{id}/submissions` as `multipart/form-data`:

- `files`: zero or more files.
- `link_url`: optional string.

Validation:

- actor must be a collaborator of the project;
- deliverable status must be `pending`, `submitted` or `changes_requested`; `approved` → `409`;
- at least one delivery method: one or more files, a valid HTTPS link, or both;
- every supplied file's extension and MIME type must be in the deliverable's `allowed_formats`;
- every supplied file's size ≤ `max_file_size_mb`;
- zero-byte files rejected;
- if any supplied file fails, reject the whole submission and store nothing;
- `link_url`, if present, must be `https://` and ≤ 2048 chars;
- lock the deliverable row, compute `max(version)+1`, create the submission and its optional files, set status to `submitted`, update project `last_modified_at`;
- append a system forum event to the same transaction;
- write files to storage and clean them up if the DB transaction fails.

Submission response includes `version`, `submitted_at`, `link_url`, and files with id, original name, MIME type, size, SHA-256. `files` may be empty for a link-only submission.

#### Review request

`POST /deliverables/{id}/reviews` as `multipart/form-data`:

- `decision`: `approved` or `changes_requested` (required).
- `files`: zero or more files (optional).

Validation:

- manager only;
- latest submission only;
- at least one submission;
- latest submission must be unreviewed;
- deliverable status must be `submitted`;
- every supplied review file uses the deliverable's `allowed_formats` and `max_file_size_mb`;
- zero-byte files rejected;
- if any supplied file fails, reject the whole review and store nothing;
- create review and its files, update deliverable status, update project `last_modified_at`;
- append one system event: the existing review event gains `y adjuntó N archivo(s)` when files are present;
- no comment field; optional forum text is posted through the existing message endpoint as a separate frontend call.

`ReviewResponse` includes the decision, reviewer, date and a `files` list with id, original name, MIME type, size and SHA-256. Review files are not a new submission version.

#### History response

Manager-only. List all submissions ordered by `version` ascending. Each item includes version, author, submitted_at, link_url, files, and its review (decision, reviewer name, reviewed_at, review files) if any.

- Collaborators receive `403` “No tienes acceso al historial de versiones.”
- Non-participants receive `404`.
- Collaborator file downloads are limited to the latest submission's files.

#### Forum

`POST /deliverables/{id}/messages`:

```json
{"body": "Revisé la versión 2; dejé los cambios en el foro."}
```

- participant only;
- trim body; empty → `422` “El comentario no puede estar vacío.”;
- max 2000 chars;
- append-only;
- creates a `kind: "user"` message with author name, author id and created_at;
- deliverable detail includes user messages and automatic `kind: "system"` lifecycle events, ordered `created_at` ascending;
- system events have `author_id: null`, `author_name: null` and are generated only by deliverable creation, edition, submission, approval or changes requested;
- no endpoint accepts or edits system events.

#### Pending reviews

`GET /reviews/pending` returns deliverables where the authenticated user is a manager and `status == submitted`, ordered by latest submission `submitted_at` ascending. Include project, milestone, deliverable title, collaborator name, version and submitted_at. This supports the “Esperan tu revisión” panel and PA-5 later; it is a derived view, not a new RF.

### 4.3 Error contract

Application errors:

```json
{"error": {"code": "INVALID_DEADLINE", "message": "Ingrese una fecha de entrega válida."}}
```

Pydantic validation errors keep FastAPI's default `422` shape (per project conventions). The frontend must handle both shapes.

| HTTP | Use |
|---|---|
| 400 | Malformed domain request not covered by 422 |
| 401 | No/invalid session; invalid login |
| 403 | Authenticated but wrong project role |
| 404 | Resource not found or user is not a project participant |
| 409 | Invalid state transition (approved upload, review without submission, etc.) |
| 422 | Field/domain validation errors |
| 500 | Unexpected error |

Stable codes (non-exhaustive): `EMPTY_CREDENTIALS`, `INVALID_CREDENTIALS`, `PROJECT_NOT_FOUND`, `FORBIDDEN`, `COLLABORATOR_REQUIRED`, `MANAGER_REQUIRED`, `PARTICIPANT_NOT_FOUND`, `DUPLICATE_ROLE`, `MILESTONE_NAME_REQUIRED`, `DELIVERABLE_FIELDS_REQUIRED`, `INVALID_DEADLINE`, `INVALID_FILE_FORMAT`, `FILE_TOO_LARGE`, `NO_FILES_OR_LINK`, `INVALID_LINK`, `SUBMISSION_NOT_ALLOWED`, `REVIEW_NOT_ALLOWED`, `MESSAGE_EMPTY`.

### 4.4 Health and docs

- `GET /health/live` → `{"status":"ok"}` without DB.
- `GET /health/ready` → checks DB; `{"status":"ok"}` or 503.
- FastAPI docs at `/api/docs`; OpenAPI at `/api/openapi.json`.
- Docker healthcheck uses `/health/live` or `/health/ready`.

---

## 5. Frontend specification

### 5.1 Routes

| Route | Screen | Access |
|---|---|---|
| `/login` | Login | Public; authenticated users redirect to `/` |
| `/` | Projects list | Authenticated |
| `/projects/new` | Create project | Professor only; otherwise 403/redirect |
| `/projects/:projectId` | Project detail | Participant |
| `/projects/:projectId/edit` | Edit project | Manager |
| `/deliverables/:deliverableId` | Deliverable detail | Participant |
| `/deliverables/:deliverableId/history` | Version history | Manager only; collaborator → 403 |
| `*` | Not found | Any |

Use an app shell for authenticated routes: header, brand, “Proyectos” nav, account menu (name, user type, “Cerrar sesión”), skip link, main landmark. No demo bar, no role switcher, no student directory, no kanban tab, no settings.

### 5.2 Screens and behavior

#### Login (`/login`)

- Brand “Hito”, subtitle “Gestión de memorias y tesis”.
- Title “Inicia sesión”; text “Entra con tu correo institucional para ver tus proyectos, entregas y revisiones.”
- Fields: “Correo institucional”, “Contraseña”.
- Button “Ingresar”.
- No “Crear cuenta”, no “¿Olvidaste tu contraseña?”, no social login.
- Empty submit → “Correo y/o contraseña vacíos.” Use `noValidate` on the form so the custom Spanish messages are shown instead of the browser's locale-dependent validation bubbles.
- Bad credentials → “Correo o contraseña incorrectos.”
- Success → `/`.
- Show a small note: “Las cuentas son creadas por el equipo operador.” (not a link).

#### Projects list (`/`)

- Greeting “Hola, {first name}”.
- Manager subtitle: “Tienes {n} entregas por revisar.” or “No tienes entregas por revisar.”
- Student subtitle: “Revisa el estado de tus entregables, sube nuevas versiones y sigue tus plazos.”
- “Nuevo proyecto” button only for user type professor.
- “Esperan tu revisión” panel for managers, from `GET /reviews/pending`:
  - deliverable title, collaborator, project/type, status chip, submission version/date, “Revisar” link;
  - empty state “No tienes entregas por revisar.”;
  - hide the panel for collaborators.
- “Tus proyectos” section:
  - sorted by last modification descending (server order);
  - each card: topic link, type + participant summary, progress `X de Y entregables aprobados`, overdue count, pending-review count for managers, next deadline among non-approved deliverables;
  - empty state “Aún no tienes proyectos.” with the appropriate help text.
- `last_modified_at` shown as “Última modificación: …”.

#### Project detail (`/projects/:id`)

- Back link “Proyectos”.
- Title = topic; subtitle type, start date, “Última modificación”.
- Participant chips with role: “Gestor”, “Colaborador”.
- Manager actions: “Editar proyecto”, “Nuevo hito”.
- No export, templates, kanban, students directory.
- “Hitos y entregables” panel:
  - if no milestones: exact “No existen hitos para este proyecto”; manager sees “Crear el primer hito”.
  - milestones sorted by order/index, numbered markers;
  - each milestone: name, derived progress `X de Y entregables aprobados`, “Nuevo entregable” (manager);
  - deliverables sorted by deadline ascending:
    - title link to detail;
    - deadline “Vence el …” / red “Venció el …” when past;
    - “Última entrega: versión N, fecha” or “Sin entregas”;
    - status chip **and** a separate “Atrasado” badge when `is_overdue`;
    - manager: “Revisar” when status is `submitted`, “Editar” always;
    - collaborator: no edit/review controls.
  - no milestone completion action or state.

#### Create project (`/projects/new`)

- Narrow form.
- Fields: “Tema del proyecto”, “Tipo de proyecto” (three types), managers, collaborators.
- Creator shown as “Tú, gestor”; cannot be removed on create.
- Add managers/collaborators by email; chips show name, role, remove button.
- Helper: “Solo puedes agregar cuentas activas. Las invitaciones llegarán en una versión posterior.”
- At least one collaborator; at least one manager (creator).
- Error messages:
  - “El proyecto requiere tener al menos un colaborador.”
  - “El proyecto requiere tener al menos un gestor.”
  - “No existe una cuenta activa con ese correo: …”
- Buttons “Cancelar”, “Crear proyecto”.
- Success → project detail.

#### Edit project (`/projects/:id/edit`)

- Same form populated with current values.
- Manager can edit topic, type, managers, collaborators.
- Same validation; removing all collaborators or managers blocks save.
- A manager may remove themselves if another manager remains; show a warning that they will lose access.
- Success → project detail.

#### Milestone dialog

- Opened from project detail (native `<dialog>`).
- Fields: “Nombre del hito”, “Ubicación” (position 1..N+1, default append).
- Error: “El Hito debe tener un nombre.”
- Buttons “Cancelar”, “Crear hito”.
- No edit milestone in this phase.

#### Deliverable dialog (create/edit)

- Fields: “Nombre del entregable”, “Descripción”, “Fecha y hora límite”, “Formatos admitidos” (checkboxes PDF/ZIP/DOCX), “Tamaño máximo por archivo (MB)” (default 50).
- No position field.
- Validation:
  - blank fields → “Los campos no pueden estar vacíos.”;
  - changed past deadline → “Ingrese una fecha de entrega válida.”;
  - help text for an already-past deadline: “La fecha ya pasó. Puedes editar otros campos sin cambiarla.”
- Buttons “Cancelar”, “Guardar entregable” / “Crear entregable”.
- Success → refresh project detail.

#### Deliverable detail (`/deliverables/:id`)

- Back link “Volver al proyecto”.
- Title, context “Hito «…», {project topic}”.
- Status panel: status chip, separate “Atrasado” badge if overdue, deadline, latest version/date.
- “Última entrega” panel:
  - version label, author, timestamp;
  - files: name, type, size, “Descargar”;
  - optional “Enlace de la entrega”;
  - collaborator note: “Solo ves la última versión entregada. Las anteriores se conservan y el equipo gestor puede verlas en el historial.”;
  - manager link: “Ver historial de versiones (N)”.
- “Tu revisión” panel (manager only, visible when status `submitted` and latest submission is unreviewed):
  - radio options “Aprobar la entrega” and “Solicitar cambios”;
  - explanatory text that the decision is recorded on version N and visible to all participants;
  - optional textarea “Mensaje para el foro (opcional)” for either decision; it is a forum message, not a review comment;
  - optional multiple-file input “Archivos de la revisión (opcional)”, using the deliverable’s formats and size limit;
  - button “Registrar revisión”;
  - after success: “Revisión registrada. Puedes dejar un comentario en el foro.” when the textarea is empty, or “Revisión registrada y mensaje publicado en el foro.” when it is posted;
  - the frontend first calls the review endpoint with the decision and review files, then, only if the textarea has content, calls the existing message endpoint;
  - if the message call fails after the review succeeds, the review remains saved and the UI reports the partial failure;
  - state conflict → “El entregable debe tener una entrega y no puede estar aprobado.” or the server message.
- Review result panel (all participants): latest review decision, reviewer, date and review files with download links; if none, “Espera revisión”.
- “Entregar una nueva versión” panel (collaborator, hidden when `approved`):
  - file input (multiple), link input;
  - text with allowed formats and max size;
  - note that files, a link, or both are accepted;
  - note that a new version replaces the visible one and preserves the previous;
  - validation errors: “Adjunta al menos un archivo válido: …” for invalid files; “Adjunta al menos un archivo válido (…) o ingresa un enlace HTTPS.” when neither method is supplied; “Ingrese un enlace HTTPS válido.” for invalid links;
  - button “Enviar entrega”.
- “Foro del entregable” panel (all participants):
  - chronological timeline with user messages and automatic lifecycle events;
  - user messages show author name + date/time;
  - system events are gray, have no author or avatar, and show date/time;
  - textarea “Escribe un mensaje”, button “Publicar mensaje”;
  - empty → “El comentario no puede estar vacío.”;
  - no edit/delete.
- Sidebar “Ficha del entregable”: project, milestone, deadline, formats, max size, version count, last update.
- No notification panel.

#### History page (`/deliverables/:id/history`, manager)

- Back link to deliverable.
- Title “Historial de versiones”.
- All versions ascending by version number; each shows version, author, timestamp, files with download, optional link, and review decision/reviewer/date plus review files if present.
- Note: “Cada entrega genera una versión nueva: ninguna se edita ni se borra.”
- Collaborator access is blocked by the route guard and the API.

### 5.3 Visual system

Reuse the deprecated mockup's visual identity; do not copy its demo scaffolding.

Tokens:

```css
--azul: #223C6A;
--azul-oscuro: #16284A;
--tinta: #1B2A45;
--suave: #44546C;
--tenue: #5E6E86;
--papel: #F5F6F9;
--blanco: #FFFFFF;
--borde: #D9DEE7;
--borde-fuerte: #8794A8;
--amarillo: #E69B0A;
--rojo: #D21428;
--ok: #1D6B3C;
--aviso: #8F5A00;
--radio: 12px;
--radio-s: 8px;
--radio-xs: 6px;
```

- Fonts: Poppins 600/700 for headings, Roboto 400/600/700 for body; copy the TTF files and OFL licences from `deprecated-mockup/fuentes/` into `frontend/public/fonts/`. Use `@font-face` with `font-display: swap`; no CDN.
- Layout: max-width 1184px; 20–32px horizontal padding; mobile-first; cards with 1px border, 12px radius, subtle shadow.
- Buttons: primary blue; secondary outlined; subtle text buttons. Minimum 44px height for touch.
- Status chips: pending gray, submitted blue, changes amber, approved green; “Atrasado” red. Always include text, not only color.
- Forms: labels above inputs, 44px min height, focus ring in blue, inline error text in red with `aria-invalid` and `aria-describedby`.
- Dialogs: native `<dialog>`, focus return, Escape close, backdrop.
- Empty states and error alerts follow the mockup's sober style.
- Responsive:
  - project/deliverable grids collapse to one column;
  - timeline margins shrink;
  - no horizontal scroll at 360px;
  - action buttons wrap;
  - file rows wrap.
- Accessibility baseline (RNF-U-1 later): semantic landmarks, one `h1` per page, skip link, visible focus, labels, `aria-live` for action feedback, `aria-current="page"`, keyboard-operable dialogs and file inputs, `prefers-reduced-motion`.
- No logos, institutional marks or real names in the UI. Demo data is fictional.

### 5.4 Frontend data layer

- `apiClient` uses `fetch` with `credentials: 'include'`, base `/api/v1`, JSON except multipart uploads.
- TanStack Query keys: `['me']`, `['projects']`, `['project', id]`, `['deliverable', id]`, `['history', id]`, `['pending-reviews']`.
- Invalidate affected keys after mutations (project create/edit, milestone, deliverable, submission, review, forum).
- 401 → clear auth state and redirect to `/login`.
- 403/404 → inline page-level alert; do not retry.
- Forms use React Hook Form + Zod; Zod messages in Spanish.
- No optimistic updates; use invalidation and loading states.
- No global state library; Query + React context for auth is enough.

---

## 6. File storage and uploads

- Define a small `StorageBackend` contract with `save`, `open`, `delete` and `exists`.
- Implement `LocalStorage` using `UPLOAD_DIR` (Docker volume). Later add `S3Storage` without changing services.
- Storage key formats:
  - submissions: `projects/{project_id}/deliverables/{deliverable_id}/submissions/{submission_id}/{file_uuid}`;
  - reviews: `projects/{project_id}/deliverables/{deliverable_id}/reviews/{review_id}/{file_uuid}`.
- Never use user-supplied paths.
- Save under a random key; store original filename separately.
- Stream the upload while:
  - enforcing `max_file_size_mb`;
  - computing SHA-256;
  - writing to a temporary file, then moving to the final key.
- Reject the entire submission or review if any supplied file fails validation.
- Store MIME type from the upload but validate against the extension allow-list:
  - `pdf`: `application/pdf`
  - `zip`: `application/zip`, `application/x-zip-compressed`
  - `docx`: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Reject zero-byte files.
- Download:
  - authenticated endpoint;
  - check project participation;
  - manager: any submission or review file in the deliverable's history;
  - collaborator: only files of the latest submission and files attached to its review;
  - return `Content-Disposition: attachment` with the original filename;
  - never expose the uploads directory through Nginx.
- Link delivery:
  - only `https://`;
  - max 2048 chars;
  - may be the only delivery method, or accompany files.
- No virus scanning, previews or public URLs in this phase; note them as later hardening.

---

## 7. Seed data and demo credentials

Idempotent seed command: `python -m app.seed`. It must be safe to run twice. Use natural keys (email, project topic). If a demo project already exists, skip its nested data.

### 7.1 Users

| Email | Name | Type | Password |
|---|---|---|---|
| `camila.soto@udec.cl` | Camila Soto | professor | `HitoDemo123!` |
| `rodrigo.pena@udec.cl` | Rodrigo Peña | professor | `HitoDemo123!` |
| `javiera.contreras@udec.cl` | Javiera Contreras | student | `HitoDemo123!` |
| `benjamin.aravena@udec.cl` | Benjamín Aravena | student | `HitoDemo123!` |
| `matias.riquelme@udec.cl` | Matías Riquelme | student | `HitoDemo123!` |
| `fernanda.torres@udec.cl` | Fernanda Torres | student | `HitoDemo123!` |
| `antonio.skorin@udec.cl` | Antonio Skorin | professor | `HitoDemo123!` |

All passwords are synthetic and documented for demo only. Never reuse them in production. The seed sets `usuario.estado = 'activa'` (API `active`) and leaves `consentimiento_fecha` and `consentimiento_version` null; RF-19 and RF-21 remain deferred. Values in the seed tables use the English API/JSON vocabulary; the seed script writes the Spanish DB values from §3.1.

### 7.2 Projects

Use deadlines relative to the seed execution date so PA-3 always works.

| Project | Type | Managers | Collaborators | Purpose |
|---|---|---|---|---|
| “Reconocimiento de gestos para interfaces sin contacto en laboratorios clínicos” | memoir | Camila, Rodrigo | Javiera | Full demo: statuses, overdue, history, forum |
| “Reconstrucción 3D de sitios patrimoniales con fotogrametría” | memoir | Camila | Benjamín | No milestones → RF-3 empty message |
| “Modelos de lenguaje para retroalimentación automática de escritura” | thesis | Camila | Matías | Second project for PA-5 |
| “Verificación formal de protocolos de consenso” | thesis | Antonio | Fernanda | Privacy test: Camila/Javiera are not participants |

For the first project, seed:

- Milestone 1 “Propuesta de memoria”:
  - “Anteproyecto” — approved (submission v2, review approved, dates in the past).
  - “Estado del arte” — approved (submission v1, review approved).
- Milestone 2 “Desarrollo y validación”:
  - “Revisión bibliográfica ampliada” — changes requested (submission v1, review changes requested, forum messages).
  - “Informe de avance 1” — submitted (v2, unreviewed, forum messages); deadline in the future.
  - “Prototipo funcional” — submitted + overdue (deadline in the past, late submission v1, unreviewed).
  - “Demostración en laboratorio” — pending (future deadline).
- Milestone 3 “Informe final y defensa”:
  - “Informe final” — pending (future deadline).
- Forum user messages with author names and dates, plus automatic lifecycle events matching the mockup's tone but fictional.

The second project has no milestones. The third has two milestones with pending deliverables. The fourth is used only for PA-4.

### 7.3 Seed rules

- Create users first; reuse by lowercased email.
- Create projects only if the topic does not exist.
- Add participants with the specified roles.
- Create submissions/reviews only inside a newly created project.
- Use UTC timestamps; display in Chile time.
- Print a short summary of created/skipped records.
- Do not run automatically in production; README documents the command.

---

## 8. Non-functional readiness (do not implement now)

The goal is to leave clean seams, not to satisfy the RNFs in this phase. The following baseline choices are unavoidable or cheap and must be respected:

| RNF | Baseline now | Later work |
|---|---|---|
| RNF-R-1 response time | Indexes, selectinload, no N+1 in list/detail, streaming uploads | Lighthouse/JMeter measurements; caching if needed |
| RNF-R-2 concurrency | Stateless API, PostgreSQL, Docker; no in-memory state | k6/Locust 100-user test; tune Uvicorn workers/pool |
| RNF-R-3 storage | File metadata (`tamano`), storage abstraction, private volume | S3 adapter, 80% storage alert, retention job |
| RNF-D-1 availability | `/health/live`, `/health/ready` | Uptime monitoring, restart policy, single-VPS plan |
| RNF-D-2 RPO/RTO | Postgres volume + documented backup command | Automated daily backups, restore drills |
| RNF-S-1 auth | Argon2id hashes, no open registration, `usuario.estado = activa` gate, 8h HttpOnly session | Lockout after 5 failures, rate limiting, password policy |
| RNF-S-2 authorization | Central RBAC dependencies and tests | Full role×action matrix, penetration review |
| RNF-S-3 transport | No secrets in code; `Secure` cookie in prod | TLS 1.2+ at Nginx/Caddy, HSTS, encryption at rest |
| RNF-U-1 accessibility | Semantic HTML, labels, focus, contrast, 44px targets | WCAG 2.1 AA audit (axe/Lighthouse) |
| RNF-U-2 responsive | Mobile-first layout, no horizontal scroll at 360px | Automated 360px browser tests |
| RNF-U-3 usability | Flows mirror the mockup and PA-1/2/5 | SUS and task-completion study |
| RNF-C-1 browsers | Modern browser APIs only | Chrome/Firefox/Safari/Edge matrix |
| RNF-C-2 file formats | Extension + MIME + size validation | Expand registry, malware scanning |
| RNF-M-1 coverage | pytest + Vitest suites; coverage report available | 80% threshold, SonarQube |
| RNF-M-2 observability | Standard app/access logs; no sensitive data | Audit table, centralized logs, retention |
| RNF-P-1 deployment | Docker Compose + Nginx | CI/CD pipeline, production TLS/deploy runbook |

Do **not** add unused services, empty interfaces or placeholder modules for these. The only RNF-oriented abstraction created now is the used `StorageBackend`/`LocalStorage` pair; settings, auth and RBAC are Must necessities.

---

## 9. Testing and verification

### 9.1 Backend tests

Use pytest + httpx `ASGITransport` against a PostgreSQL test database (`hito_test`), with Alembic migrations applied once per session and table truncation between tests. The Postgres init script must create both `hito` and `hito_test`. Use a temporary upload directory per test.

Required coverage:

- **Auth:** correct login; invalid password; empty fields; unknown account; session cookie; `/me`; logout; no registration endpoint; Argon2 hash not plaintext.
- **Projects:** list only participating; sorted by `last_modified_at`; professor-only create; creator manager; no collaborators; unknown email; duplicate role; manager edit; collaborator forbidden; remove all collaborators/managers blocked; non-participant 404.
- **Milestones/deliverables:** manager create milestone with position shifting; empty name; manager create/edit deliverable; blank fields; past deadline on create; changed past deadline on edit rejected; unchanged past deadline allowed; collaborator forbidden; invalid formats/size.
- **Submissions:** collaborator uploads v1; multiple files; link-only submission; files plus link; status becomes submitted; late upload accepted with real timestamp and overdue; re-upload while submitted creates v2 and stays submitted; approved upload 409; manager upload 403; invalid format/MIME/size/zero-byte; missing files and link; invalid link; whole submission rejected on one bad file; local storage key and SHA-256; download permissions (manager all, collaborator latest, non-participant 404).
- **Reviews:** manager approves/changes with no files; optional multiple review files; same allowed format/MIME/size/zero-byte validation as submissions; invalid review file rolls back the review; status transitions; review only latest/unreviewed/submitted; no submission 409; collaborator 403; approved terminal; one review per submission; history and detail include review files; manager and latest-review collaborator can download review files; older review files are blocked for collaborators; non-participants receive 404; review event mentions attached file count.
- **Overdue:** pure function cases (future, exactly deadline, past no submission, past late submission, past on-time submission with changes requested, approved) plus API responses.
- **Forum:** participant post/list; empty body; non-participant 404; chronological order; user author/date; automatic lifecycle events for creation, edition, submission and review; system events have no author.
- **Seed:** idempotent run; demo accounts; PA-3 data.
- **Acceptance flows:** PA-1, PA-2, PA-3, PA-4 as integration tests across the API.

### 9.2 Frontend tests

Vitest + React Testing Library with mocked `fetch`:

- login empty/invalid/success; no sign-up link;
- projects list empty/populated, pending-review panel, role-based “Nuevo proyecto”;
- project detail no-milestones message; ordering; status + overdue badges; manager vs collaborator controls;
- create/edit project validation; participant chips; unknown email error;
- milestone dialog name/position;
- deliverable dialog fields, formats, max size, past deadline warning/error;
- deliverable detail: latest submission, file upload, link-only submission, files plus link, review form with optional forum message and review files, review result with review-file downloads, history link visibility, history review-file downloads, forum user messages and gray system events, collaborator history hidden;
- routing guards: 401 → login; collaborator history → blocked; non-participant error;
- accessibility basics: labels, `aria-invalid`, focusable dialog, status text.

No Playwright/browser E2E in this phase; add it later with RNF-U-2/RNF-U-3. PA-1..PA-4 are covered at the API integration level plus component tests. A manual browser walkthrough is part of the final verification.

### 9.3 Acceptance scenarios

| ID | Steps | Expected |
|---|---|---|
| PA-1 | Professor logs in; creates project; adds two milestones; adds deliverable with future deadline; adds student collaborator; student logs in | Project appears for both; student sees milestones/deliverable; creator is manager |
| PA-2 | Collaborator uploads v1; manager requests changes; manager posts forum comment; collaborator uploads v2; manager approves | States: submitted → changes_requested → submitted → approved; history has v1 and v2 with v1 review; forum comment visible |
| PA-3 | Deliverable deadline passes with no submission; later collaborator submits | `is_overdue` true before and after late submission; status `submitted`; real timestamp stored; badge disappears only after approval |
| PA-4 | Student opens another project's URL/API | 404/blocked; no project data leaked |

### 9.4 Commands

```bash
# app
cp .env.example .env
docker compose up --build -d
docker compose exec backend python -m app.seed
# open http://localhost:8080

# backend tests (development target/service, profile "test")
docker compose --profile test run --rm backend-test pytest
docker compose --profile test run --rm backend-test ruff check app tests
docker compose --profile test run --rm backend-test pyright

# frontend checks
cd frontend
npm ci
npm run lint
npm run typecheck
npm run test -- --run
npm run build
```

If the development service is not used, document the equivalent local commands in `README.md`. Do not claim verification without running them.

---

## 10. Implementation order

1. **Scaffold:** repo layout, `.gitignore`, `.env.example`, Docker Compose, Postgres, FastAPI health, Alembic, base settings/errors, frontend Vite shell.
2. **Auth:** users, sessions, Argon2, login/logout/me, cookie, auth dependency, seed users.
3. **Projects:** models, schemas, create/list/detail/edit, participant validation, RBAC dependencies.
4. **Milestones/deliverables:** create milestone with order, create/edit deliverable, deadline rules, state defaults, project detail aggregation.
5. **Submissions/files:** storage abstraction, multipart validation, versioning, immutable history, download permissions.
6. **Reviews/overdue:** state machine, review endpoint, overdue pure function, project counts, pending-review endpoint.
7. **Forum:** messages model with user/system types, list/post, validation, automatic lifecycle events, deliverable detail inclusion.
8. **Frontend shell/auth/projects:** app shell, login, projects list, pending reviews, create/edit project.
9. **Frontend project detail/forms:** milestone dialog, deliverable dialog, timeline, statuses/badges.
10. **Frontend deliverable:** detail, upload, review, history, forum, role-based visibility.
11. **Seed/demo/docs:** full demo data, README, API docs, manual acceptance walkthrough.
12. **Verification:** backend tests/lint/typecheck, frontend tests/lint/typecheck/build, Docker Compose smoke, PA-1..PA-4 manual/browser check.

Do not proceed to Should/Could features (RF-7, RF-15–RF-21) before all Must RFs and PA-1..PA-4 pass.

---

## 11. Traceability

| RF | API | UI | Key RBs | Tests |
|---|---|---|---|---|
| RF-1 | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` | Login | RB-20 (seed-only) | auth tests |
| RF-2 | `GET /projects` | Projects list | RB-4 | list/sort/RBAC tests |
| RF-3 | `GET /projects/{id}` | Project detail | RB-4 | detail/order/empty tests |
| RF-4 | `POST /projects` | Create project | RB-1, RB-2, RB-3 | create/validation tests |
| RF-5 | `PATCH /projects/{id}` | Edit project | RB-2, RB-3, RB-4, RB-5 | edit/RBAC tests |
| RF-6 | `POST /projects/{id}/milestones` | Milestone dialog | RB-5 | milestone tests |
| RF-8 | `POST /milestones/{id}/deliverables` | Deliverable dialog | RB-5, RB-6, RB-8 | create/validation tests |
| RF-9 | `PATCH /deliverables/{id}` | Deliverable dialog | RB-5, RB-6, RB-8 | edit/deadline tests |
| RF-10 | `POST /deliverables/{id}/submissions` | Upload panel | RB-7, RB-8, RB-10 | upload/link/version/overdue tests |
| RF-11 | `POST /deliverables/{id}/messages`; detail includes user messages and system events | Forum panel | RB-15 | forum tests |
| RF-12 | `GET /deliverables/{id}/submissions` | History page | RB-17 | history/permission tests |
| RF-13 | detail/list responses include `status`, `is_overdue` | Status chips + badge | RB-9, RB-10 | overdue/state tests |
| RF-14 | `POST /deliverables/{id}/reviews` with optional files | Review panel | RB-9, RB-11 | review/state/file tests |

---

## 12. Error messages and user-facing text

Use Spanish (Chile), sentence case, no jargon. Exact or near-exact messages required by the SRS:

- “Correo y/o contraseña vacíos.”
- “Correo o contraseña incorrectos.”
- “No existen hitos para este proyecto.”
- “El proyecto requiere tener al menos un colaborador.”
- “El proyecto requiere tener al menos un gestor.”
- “El Hito debe tener un nombre.”
- “Los campos no pueden estar vacíos.”
- “Ingrese una fecha de entrega válida.”
- “El comentario no puede estar vacío.”
- “No tienes acceso al historial de versiones.”
- “No encontrado o no tienes acceso a este proyecto.”
- “El entregable debe tener una entrega y no puede estar aprobado.”
- “Adjunta al menos un archivo válido: {formatos}.”
- “Adjunta al menos un archivo o ingresa un enlace HTTPS válido.”
- “Ingrese un enlace HTTPS válido.”
- “El formato del archivo no está permitido: {nombre}.”
- “El archivo {nombre} está vacío.”
- “El archivo {nombre} supera el tamaño máximo de {tamaño} MB.”
- “No existe una cuenta activa con ese correo: {email}.”
- “Un usuario no puede tener dos roles en el mismo proyecto.”

Status labels: “Pendiente”, “Entregado”, “Cambios solicitados”, “Aprobado”; badge “Atrasado”. Roles: “Gestor”, “Colaborador”. Types: “Memoria de título”, “Tesis”, “Proyecto de investigación”.

---

## 13. Definition of Done

- All 13 Must RFs implemented; no Should/Could UI leaked in.
- PA-1, PA-2, PA-3 and PA-4 pass.
- Backend tests, frontend tests, lint, type-check and build pass.
- `docker compose up --build` starts db + backend + web; seed command works; demo login works.
- Alembic migration is committed and applies to a fresh database.
- Seed is idempotent.
- README documents setup, demo accounts, commands, scope and RNF extension points.
- No secrets in code; `.env` ignored; demo passwords documented as synthetic.
- The application implementation does not modify `deprecated-mockup/`; `main.tex` is updated only as a separate, explicitly approved documentation task (§14).
- No raw passwords/tokens/file contents in logs.
- No dead code, TODOs, stubs or fake implementations.
- Code comments/public docs in Spanish; identifiers in English; UI in Spanish.
- RNF seams are present and documented, but RNF acceptance work is not claimed.

---

## 14. SRS updates to apply later (not in Plan mode)

When explicitly approved in Build mode, update `main.tex` to match the resolved decisions:

1. **RF-11 priority:** change Should → Must in §3.1 and §9.1. Update the counts in the executive summary and §9.1 (13 Must, 5 Should, 3 Could) and include RF-11 in the MVP definition.
2. **PA-2:** state that the review comment is a forum message; the review itself records only the decision.
3. **§5.1 Revisión:** remove the `comentario` attribute; keep decision and date. `Comentario` is the deliverable forum.
4. **RF-8 / §5.1 Entregable:** remove the manual position/order from deliverables; state that they are ordered by deadline. Keep `orden` for milestones.
5. **RB-6:** clarify that editing an already overdue deliverable is allowed if the stored past deadline is unchanged; only a changed past deadline is rejected.
6. **RB-9 / RF-10:** document the allowed `Entregado → Entregado` re-upload self-transition; `Aprobado` remains terminal.
7. **RF-10:** note the optional HTTPS link alongside mandatory files.
8. **Existing RF-11 detail:** add a short RF-11 detail table (actors, preconditions, main flow, criteria) matching the promoted Must status.
9. **Data model:** ensure `Revisión` has no comment and `Comentario` belongs to `Entregable`.

The generic `created_at`/`modified_at` audit columns are implementation additions and do not require SRS text changes; the SRS business timestamps remain in the schema.

Do not apply these edits silently. They are documentation changes to the SRS, separate from the application implementation.

---

## 15. Assumptions and risks

- Seeded accounts are enough for the Must demo; RF-19 is deferred. Participant emails must exist.
- The seed uses synthetic data and relative deadlines; no real student data.
- Local file storage is used; S3 and signed URLs are later.
- No email notifications; forum and in-app state are the communication channel.
- The deadline is a timezone-aware datetime, not a date-only value. UI displays Chile time.
- The manager review has no comment field; comments are forum messages.
- A collaborator may re-upload while `Entregado`; this is intentional per the user's decision.
- No browser E2E now; API integration + component tests cover PA-1..PA-4. Playwright is a later RNF-enablement task.
- Docker is required for the documented runtime; the host has Python 3.14, but the backend container uses Python 3.13.
- The SRS remains the requirements source; where this document resolves an ambiguity, the resolution is recorded in §1.3 and §14.
