# Cambios propuestos a `main.tex` — requisitos no funcionales

**Versión:** 1.0  
**Fecha:** 16 de noviembre de 2026  
**Documento de referencia:** `spec/main.tex`  
**Plan de pruebas asociado:** `spec/nfr-test-plan.md`  
**Estado:** propuesta; `main.tex` no se modifica en esta fase

## 1. Regla de este documento

`main.tex` es la fuente de requisitos y no se edita sin una instrucción explícita. Este archivo enumera **todos** los cambios de tecnología, método de verificación y decisión de alcance que deberían aplicarse al SRS para que el documento y la implementación queden consistentes.

Cada cambio indica:

- la sección o fila afectada;
- el texto actual;
- el texto propuesto;
- el motivo;
- el impacto sobre el resto del documento.

## 2. Resumen de sustituciones tecnológicas

| Área | Texto actual del SRS | Decisión adoptada | Motivo |
|---|---|---|---|
| Rendimiento de navegación (RNF-R-1) | Google Lighthouse | Playwright con Performance API; Lighthouse queda como complemento opcional | Permite medir páginas autenticadas y navegación SPA de forma repetible. |
| Carga y concurrencia (RNF-R-1, RNF-R-2) | JMeter | Generador asíncrono en Python con `httpx` | Evita una dependencia Java/JVM y se integra con el stack y el CI del proyecto. |
| Accesibilidad (RNF-U-1) | Google Lighthouse | `axe-core` sobre Playwright + checklist manual WCAG 2.1 AA | Lighthouse no cubre bien páginas autenticadas ni estados de diálogos; axe permite reglas WCAG específicas. |
| Cobertura (RNF-M-1) | SonarQube | `pytest-cov` con umbral de 80 % | `pytest-cov` ya está en el entorno; SonarQube no está desplegado y añade infraestructura no justificada. |
| Navegadores (RNF-C-1) | Pruebas automatizadas de UI | Playwright en Chromium, Firefox y WebKit; checklist manual de versiones penúltimas | Es repetible en CI; las versiones penúltimas y los binarios reales de Safari/Edge se revisan manualmente. |
| TLS (RNF-S-3) | Auditoría de certificados SSL | Handshake TLS 1.2/1.3 con certificados autofirmados en local + SSL Labs en producción | No hay dominio ni certificado de producción todavía; se verifica lo automatizable y se documenta lo pendiente. |
| Logs centralizados (RNF-M-2) | Guardado de logs en la nube | Auditoría en base + logs JSON a stdout + runbook CloudWatch/Loki | No hay proveedor de logs configurado; la auditoría en base es la evidencia local y el envío a la nube queda documentado. |
| Almacenamiento (RNF-R-3) | Monitoreo del almacenamiento de objetos | Reporte local de volumen + metadatos, alerta al 80 % + runbook S3/ciclo de vida | El adaptador de objetos no está implementado; el reporte local es verificable y el runbook cubre producción. |
| Respaldos (RNF-D-2) | Simulacros semestrales | Respaldo diario automatizado + simulacro de restauración reproducible | Convierte el simulacro en una prueba repetible y medible, no en una actividad manual sin evidencia. |
| CI/CD (RNF-P-1) | Revisión del pipeline CI/CD | GitHub Actions con jobs de calidad, tests, cobertura, Docker, E2E y NFR | El repositorio no tiene pipeline; se crea uno versionado y ejecutable. |
| Disponibilidad (RNF-D-1) | Monitoreo de uptime con Pingdom | Sin verificación automática en esta fase; monitor externo pendiente | No hay cuenta/evidencia externa y un monitor local no demuestra disponibilidad mensual. |
| Responsivo (RNF-U-2) | Pruebas en navegadores móviles iOS/Android | Playwright a 360×800 + emulación Pixel/iPhone; dispositivos físicos manual | La emulación es repetible en CI; los dispositivos reales quedan como verificación manual. |
| Formatos (RNF-C-2) | Pruebas de integración del endpoint de subida | Matriz de extensión, MIME, tamaño y atomicidad; sin magic bytes | Refuerza la verificación, pero deja explícita la limitación de confiar en el MIME declarado. |

## 3. Cambios por requisito

### 3.1 RNF-R-1 — Tiempo de respuesta p95

**Ubicación:** §4, tabla “Rendimiento y capacidad”, columna “Método de verificación”.

**Texto actual:**

> Pruebas de navegación con Google Lighthouse y de carga usando JMeter

**Texto propuesto:**

> Medición de navegación con Playwright (Performance API) y prueba de carga con generador asíncrono en Python (`httpx`). Lighthouse puede usarse como auditoría complementaria opcional. Los umbrales p95 ≤ 500 ms en navegación y ≤ 3 s en subida se bloquean en el VPS y se reportan sin bloqueo en CI local.

**Motivo:** el SRS exige medir navegación autenticada y subida de archivos. Lighthouse no mide bien flujos autenticados ni transiciones SPA, y JMeter añade una dependencia pesada. Playwright ya se necesita para RNF-U-1, RNF-U-2 y RNF-C-1.

**Impacto:** cambia solo el método de verificación; el objetivo y la justificación del valor no cambian. La evidencia se guarda en `reports/nfr/navigation.json`.

**Estado de implementación (17-11-2026):** implementado; falta la ejecución completa en VPS.

- `frontend/e2e/perf.spec.ts` mide portafolio, detalle de proyecto, detalle de entregable y una subida de 10 MB con Playwright/Chromium.
- El smoke local con dataset SRS completo dio p95 ≤ 97 ms en navegación y ≤ 153 ms en subida.
- `E2E_PERF_ENFORCE=1` bloquea si se superan 500 ms de navegación o 3 s de subida.
- La ejecución VPS queda pendiente de acceso al dominio.

### 3.2 RNF-R-2 — Concurrencia de usuarios

**Ubicación:** §4, tabla “Rendimiento y capacidad”, columna “Método de verificación”.

**Texto actual:**

> Prueba de estrés con JMeter sobre datos sintéticos

**Texto propuesto:**

> Prueba de carga con generador asíncrono en Python sobre datos sintéticos a escala completa: 100 usuarios concurrentes durante 15 minutos, mezcla 80 % lecturas / 15 % descargas / 5 % escrituras, y verificación de p95 de RNF-R-1 y tasa de error < 1 %. La ejecución bloquea en el VPS y reporta en CI local.

**Motivo:** el generador permite controlar la mezcla, las sesiones y el dataset; JMeter no aporta una ventaja proporcional al costo de mantenerlo. La mezcla y el dataset quedan explícitos para que la prueba sea reproducible.

**Impacto:** el objetivo no cambia. Se agrega una descripción operativa del perfil de carga que el SRS no detalla.

**Estado de implementación (17-11-2026):** implementado; falta la ejecución completa en VPS.

- `backend/app/seed_perf.py` genera el escenario completo, con guardas para no ejecutarse fuera de una base `perf`.
- `scripts/nfr/load_test.py` corre 100 usuarios/15 min con mezcla 80 % lecturas, 15 % descargas y 5 % escrituras; reporta p50/p95/p99, errores y throughput.
- `scripts/nfr/perf.sh` levanta `hito_perf`, siembra, ejecuta carga, navegación y memoria; `PERF_ENFORCE=1` bloquea.
- `scripts/nfr/memory_sampler.py` y `memory_report.py` registran el pico de RAM de `backend`, `db` y `web`, excluyendo el generador de carga.
- Smoke local: 10 usuarios/30 s, 307 requests, error rate 0, p95 29 ms; pico de RAM 182 MiB.
- La ejecución de 100 usuarios/15 min se programa nightly y en `perf-vps.yml`; el VPS sigue pendiente.

### 3.3 RNF-R-3 — Volumen de datos y crecimiento

**Ubicación:** §4, tabla “Rendimiento y capacidad”, columna “Método de verificación”.

**Texto actual:**

> Monitoreo del uso del almacenamiento de objetos, con alerta al 80 % de lo previsto

**Texto propuesto:**

> Reporte `storage_report.py` sobre el volumen local de subidas y los metadatos de `archivo.tamano`, con cuota de 100 GB y alerta al 80 %. En producción se complementa con el runbook de S3, ciclo de vida y AWS Budgets. La retención de 12 meses posterior al cierre del proyecto queda como dependencia pendiente.

**Motivo:** el adaptador de almacenamiento de objetos no está implementado; el almacenamiento actual es un volumen local. El reporte local sí es verificable y el runbook cubre la transición a S3.

**Impacto:** el objetivo de 33–66 GB/año y ≤ 100 GB no cambia. Se explicita que el cálculo de régimen depende de la retención, que aún no está implementada.

**Estado de implementación (17-11-2026):** implementado el reporte local; producción pendiente.

- `backend/app/core/storage_report.py` calcula bytes reales del volumen, bytes registrados en `archivo.tamano`, cuota de 100 GB, alerta al 80 % y diferencia > 5 %.
- `scripts/nfr/storage_report.sh` lo ejecuta en el backend y escribe `reports/nfr/storage.json`.
- Códigos de salida: `0` ok, `2` warning, `1` crítico.
- `backend/tests/test_nfr_storage.py` cubre umbrales, discrepancia y tamaño de directorio.
- `docs/operations/storage.md` documenta S3, ciclo de vida y AWS Budgets; no hay bucket ni retención de 12 meses implementados.
- El workflow `nfr-nightly.yml` ejecuta el reporte de almacenamiento y publica `storage-report` como artefacto.

### 3.4 RNF-D-1 — Disponibilidad

**Ubicación:** §4, tabla “Disponibilidad y continuidad”, columna “Método de verificación”.

**Texto actual:**

> Monitoreo de uptime con Pingdom

**Texto propuesto:**

> Monitoreo de uptime con Pingdom o equivalente externo (pendiente de configurar). En esta fase no se verifica automáticamente; se mantiene el objetivo de ≥ 99,5 % mensual y se registra la falta de evidencia como brecha.

**Motivo:** no hay cuenta de Pingdom, dominio de producción ni un mes de datos. Un chequeo local no demuestra disponibilidad mensual y afirmar cumplimiento sin evidencia sería incorrecto.

**Impacto:** el objetivo no cambia, pero el SRS debe dejar claro que la verificación está pendiente. No se debe declarar RNF-D-1 como cumplido en el informe final.

### 3.5 RNF-D-2 — RPO / RTO

**Ubicación:** §4, tabla “Disponibilidad y continuidad”, columna “Método de verificación”.

**Texto actual:**

> Simulacros semestrales de recuperación

**Texto propuesto:**

> Respaldo diario automatizado de PostgreSQL y del volumen de subidas, con retención local de 30 días, y simulacro de restauración reproducible (`backup_restore_drill.sh`) que verifica conteos y SHA-256 y mide el RTO. Se ejecuta en nightly/manual y se programa semestralmente en producción.

**Motivo:** un simulacro semestral sin script no es repetible ni medible. El procedimiento automatizado produce evidencia de RPO 24 h y RTO 4 h.

**Impacto:** se mantiene el objetivo. Se agrega el alcance local y se aclara que la copia fuera del servidor queda pendiente para producción.

**Estado de implementación (17-11-2026):** implementado el respaldo y el simulacro local; copia offsite pendiente.

- `scripts/nfr/backup.sh` genera `pg_dump -Fc`, `tar --sparse` de subidas, SHA-256, tamaños, conteos y cantidad de archivos en `backups/`.
- `scripts/nfr/restore_drill.sh` verifica hashes y antigüedad, restaura en un PostgreSQL desechable, compara conteos y archivos, mide RTO y escribe `reports/nfr/restore-drill.json`.
- Retención local de 30 días; RPO 24 h y RTO 4 h configurables.
- `.github/workflows/nfr-nightly.yml` ejecuta el respaldo, el simulacro y el reporte de almacenamiento.
- `docs/operations/backup-restore.md` documenta el procedimiento y deja pendientes la copia offsite y el cifrado en reposo.

### 3.6 RNF-S-1 — Autenticación

**Ubicación:** §4, tabla “Seguridad”, columnas “Métrica o control” y “Método de verificación”.

**Texto actual (control):**

> Autenticación propia con correo institucional y contraseña: 100 % de las contraseñas almacenadas como hash (bcrypt o Argon2), bloqueo temporal de la cuenta tras 5 intentos fallidos consecutivos y ninguna vía de registro abierto.

**Texto propuesto (control):**

> Autenticación propia con correo institucional y contraseña: 100 % de las contraseñas almacenadas como hash Argon2id, bloqueo de la cuenta durante 15 minutos tras 5 intentos fallidos consecutivos y ninguna vía de registro abierto. La respuesta de cuenta bloqueada es HTTP 423 con un mensaje explícito; un inicio de sesión exitoso reinicia el contador.

**Texto actual (verificación):**

> Pruebas de integración del inicio de sesión e inspección del esquema de la base de datos

**Texto propuesto (verificación):**

> Pruebas de integración de hash Argon2id, bloqueo/desbloqueo a los 15 minutos, reinicio del contador, ausencia de rutas de registro y flags de cookie; inspección del esquema de la base de datos.

**Motivo:** el SRS no fija la duración del bloqueo ni el código de respuesta, lo que impide una prueba objetiva. La implementación usa Argon2id y necesita una especificación verificable.

**Impacto:** el objetivo de seguridad no cambia; se agregan parámetros concretos y se elimina la ambigüedad entre bcrypt y Argon2.

**Estado de implementación (16-11-2026):** implementado.

- `MAX_FAILED_LOGIN_ATTEMPTS=5` y `LOGIN_LOCKOUT_MINUTES=15` en `backend/app/core/config.py`, `.env.example` y `compose.yaml`.
- Columnas `intentos_fallidos` y `bloqueado_hasta` en `usuario`, con migración `7a1c3e5b9d2f_add_login_lockout_fields.py`.
- El quinto fallo consecutivo responde 401 y deja la cuenta bloqueada; el sexto intento responde 423 con el mensaje configurado.
- Un login exitoso reinicia el contador; un bloqueo vencido se limpia antes del siguiente intento.
- Pruebas agregadas en `backend/tests/test_auth.py`: bloqueo, expiración, reinicio, correo inexistente, hash Argon2id y ausencia de rutas de registro.

### 3.7 RNF-S-2 — Autorización y privacidad

**Ubicación:** §4, tabla “Seguridad”, columna “Método de verificación”.

**Texto actual:**

> Test unitarios, de integración y de uso por un usuario final del sistema

**Texto propuesto:**

> Matriz automatizada rol × endpoint (anónimo, no participante, colaborador, gestor y otro gestor), pruebas de versión/historial/descarga, pruebas de componente de la interfaz y E2E de PA-4. La matriz cubre todas las rutas OpenAPI y falla si aparece una ruta sin clasificar.

**Motivo:** la frase actual es genérica y no garantiza cobertura exhaustiva. La matriz convierte RBAC en una verificación repetible y evita que una ruta nueva quede sin control de acceso.

**Impacto:** se mantiene el objetivo de RBAC estricto. Se agrega una obligación de mantenimiento: toda ruta nueva debe registrarse en la matriz.

**Estado de implementación (16-11-2026):** implementado en backend.

- `backend/tests/test_nfr_rbac.py` clasifica las 19 rutas OpenAPI y falla si aparece una ruta sin clasificar.
- Pruebas de acceso anónimo, no participante (404), colaborador en acciones de gestor (403), gestor en acciones de colaborador (403), lectura por rol, inbox de revisiones, historial y descargas.
- Las pruebas de componente y el E2E de PA-4 quedan pendientes para la fase de navegador.

### 3.8 RNF-S-3 — Protección de datos

**Ubicación:** §4, tabla “Seguridad”, columna “Método de verificación”.

**Texto actual:**

> Auditoría de certificados SSL

**Texto propuesto:**

> Prueba de handshake TLS 1.2/1.3 con certificados autofirmados en el perfil local, revisión estática de la configuración (solo TLS 1.2/1.3, HSTS y redirección HTTP→HTTPS) y auditoría SSL Labs del dominio de producción cuando esté disponible.

**Motivo:** no hay dominio ni certificado de producción. La prueba local verifica los protocolos y la configuración; SSL Labs queda como evidencia pendiente de producción.

**Impacto:** el objetivo TLS 1.2+ no cambia. Se distingue explícitamente entre verificación local y auditoría de producción.

**Estado de implementación (17-11-2026):** implementado el perfil local; producción pendiente.

- `scripts/nfr/generate_tls_certs.sh` genera certificados autofirmados en `certs/` (ignorado por Git).
- `frontend/nginx.tls.conf` configura TLS 1.2/1.3, HSTS y redirección HTTP→HTTPS.
- `compose.tls.yaml` ejecuta un proyecto Compose separado (`hito_tls`), sin exponer el backend y con `SESSION_COOKIE_SECURE=true` y `TRUST_PROXY_HEADERS=true`.
- `scripts/nfr/tls_smoke.sh` levanta el perfil, siembra datos y ejecuta `scripts/nfr/tls_check.py`.
- `tls_check.py` verifica handshakes 1.2/1.3, rechazo de 1.0/1.1, HTTPS, HSTS, redirección y cookie `Secure`.
- CI agrega el job `tls-handshake`.
- `docs/operations/tls.md` documenta Certbot y SSL Labs para producción; no hay dominio ni certificado real todavía.

### 3.9 RNF-U-1 — Accesibilidad

**Ubicación:** §4, tabla “Usabilidad y accesibilidad”, columna “Método de verificación”.

**Texto actual:**

> Auditoría con Google Lighthouse

**Texto propuesto:**

> Auditoría automatizada con `axe-core` sobre Playwright usando las etiquetas WCAG 2.1 A/AA, pruebas de teclado y foco, y checklist manual WCAG 2.1 AA para lo que las herramientas no cubren. Lighthouse puede usarse como complemento opcional.

**Motivo:** Lighthouse no permite auditar fácilmente páginas autenticadas ni estados de diálogos, y su puntaje de accesibilidad no equivale a conformidad WCAG. `axe-core` permite reglas y etiquetas específicas.

**Impacto:** el objetivo WCAG 2.1 AA no cambia. Se aclara que la conformidad completa requiere checklist manual.

**Estado de implementación (17-11-2026):** implementado el subconjunto automatizable.

- `frontend/e2e/a11y.spec.ts` ejecuta axe-core con etiquetas WCAG 2.1 A/AA en login, portafolio, formulario, proyecto, edición, entregable, historial y 404.
- `frontend/e2e/keyboard.spec.ts` cubre orden de tabulación, skip link, cierre de diálogo con Escape y retorno de foco.
- `docs/nfr/wcag-manual-checklist.md` contiene la checklist manual pendiente de ejecución.
- Las auditorías axe se ejecutan en Chromium; Firefox/WebKit ejecutan el smoke funcional. Firefox presentó un crash de página al ejecutar axe y se excluyó para mantener el nightly estable.

### 3.10 RNF-U-2 — Diseño responsivo

**Ubicación:** §4, tabla “Usabilidad y accesibilidad”, columna “Método de verificación”.

**Texto actual:**

> Pruebas en navegadores móviles (iOS/Android)

**Texto propuesto:**

> Pruebas Playwright a 360×800 con emulación de Pixel 5 e iPhone 12, verificando ausencia de desplazamiento horizontal y ejecución completa de PA-1, PA-2 y PA-5. La verificación en dispositivos físicos iOS/Android queda como comprobación manual.

**Motivo:** la emulación es repetible en CI y cubre el ancho exigido; los dispositivos físicos no están disponibles de forma automatizada.

**Impacto:** el objetivo del 100 % de tareas a 360 px no cambia. Se documenta la diferencia entre emulación y dispositivo real.

**Estado de implementación (17-11-2026):** implementado en Chromium.

- `frontend/e2e/responsive.spec.ts` ejecuta PA-1, PA-2 y PA-5 a 360×800 y verifica ausencia de scroll horizontal.
- Los cuatro tests pasan en Chromium.
- La verificación en dispositivos físicos iOS/Android sigue pendiente y se registra como limitación.

### 3.11 RNF-U-3 — Facilidad de uso sin capacitación

**Ubicación:** §4, tabla “Usabilidad y accesibilidad”, columna “Método de verificación”; y §10, “Plan de validación con usuarios”.

**Texto actual:**

> Validación de uso sobre el prototipo con 3 a 5 profesores (§10)

**Texto propuesto:**

> Validación de uso con 3 a 5 profesores guía, tareas PA-1, PA-2 y PA-5 sin ayuda, registro de éxito/tiempo/errores y cuestionario SUS. Criterios: ≥ 85 % de tareas completadas sin ayuda en el primer intento y SUS ≥ 68. El protocolo, el cuestionario y la plantilla de resultados están en `docs/nfr/`.

**Motivo:** el SRS ya fija los criterios en §10; el cambio los hace trazables a artefactos concretos y a un procedimiento reproducible.

**Impacto:** el objetivo no cambia. La ejecución sigue siendo manual y sus resultados se registran en el Anexo B, no en el repositorio.

**Estado de implementación (17-11-2026):** artefactos creados; ejecución pendiente.

- `docs/nfr/usability-protocol.md` define participantes, reglas, tareas PA-1/PA-2/PA-5 y criterios.
- `docs/nfr/sus-form.md` contiene el cuestionario SUS y su cálculo.
- `docs/nfr/results-template.md` registra tareas, SUS, hallazgos y acciones.
- No se han ejecutado sesiones con profesores; los resultados siguen pendientes para el Anexo B.

### 3.12 RNF-C-1 — Navegadores soportados

**Ubicación:** §4, tabla “Compatibilidad e interoperabilidad”, columna “Método de verificación”.

**Texto actual:**

> Pruebas automatizadas de UI y desarrollo que excluya funcionalidades experimentales

**Texto propuesto:**

> Smoke Playwright en Chromium, Firefox y WebKit; Chromium en cada PR y matriz completa en nightly/manual. Checklist manual de las versiones penúltimas de Chrome, Edge, Firefox y Safari. Se excluyen APIs experimentales y se mantiene un target de build conservador.

**Motivo:** Playwright permite automatizar tres motores; Edge comparte Chromium y Safari se aproxima con WebKit. Las versiones penúltimas y los binarios reales no se pueden cubrir de forma automatizada con el entorno actual.

**Impacto:** el objetivo de los cuatro navegadores no cambia. Se explicita la equivalencia de motores y la verificación manual pendiente.

**Estado de implementación (17-11-2026):** implementado el smoke multi-motor.

- `frontend/e2e/browser-smoke.spec.ts` y los flujos PA se ejecutan en proyectos Playwright Chromium, Firefox y WebKit.
- Chromium y Firefox pasan localmente; WebKit requiere dependencias del sistema y se ejecuta en CI con `npx playwright install --with-deps`.
- El checklist de versiones penúltimas de Chrome, Edge, Firefox y Safari sigue pendiente para la release.

### 3.13 RNF-C-2 — Formatos de archivo

**Ubicación:** §4, tabla “Compatibilidad e interoperabilidad”, columna “Método de verificación”.

**Texto actual:**

> Pruebas de integración en endpoint de subida

**Texto propuesto:**

> Matriz de pruebas de integración: PDF, ZIP y DOCX con MIME permitido; extensiones en mayúsculas; varios archivos; archivo + enlace; solo enlace; rechazo por extensión, MIME ausente/incorrecto, tamaño, archivo vacío y rechazo atómico de la entrega completa. No se validan magic bytes; la limitación se documenta.

**Motivo:** la frase actual no especifica los casos y no deja claro el alcance de la validación. La matriz cubre los criterios de aceptación de RF-10 y RB-8.

**Impacto:** el objetivo no cambia. Se agrega una limitación de seguridad explícita.

**Estado de implementación (16-11-2026):** implementado.

- `backend/tests/test_nfr_uploads.py` cubre PDF, ZIP (dos MIME), DOCX, extensión en mayúsculas, múltiples archivos, archivo + enlace, solo enlace, MIME incorrecto/ausente, archivo vacío, tamaño excedido, enlace no HTTPS y rechazo atómico.
- Se verifica que una entrega rechazada no crea versión ni deja el entregable en estado distinto de `pending`.
- La ausencia de validación de magic bytes queda documentada como limitación.

### 3.14 RNF-M-1 — Cobertura de pruebas

**Ubicación:** §4, tabla “Mantenibilidad y calidad interna”, columna “Método de verificación”.

**Texto actual:**

> Sondeo de cobertura usando SonarQube

**Texto propuesto:**

> Cobertura con `pytest-cov` sobre la lógica de negocio: `auth/security.py`, `auth/service.py`, `deliverables/dependencies.py`, `deliverables/service.py`, `projects/dependencies.py`, `projects/service.py`, `storage/service.py`, `api/deps.py`, `core/errors.py` y `core/audit/service.py`. Umbral de 80 % de línea; se reporta cobertura de ramas como métrica complementaria. El reporte XML/HTML se publica en CI.

**Motivo:** SonarQube no está desplegado y añade infraestructura no justificada. `pytest-cov` ya está disponible y permite fijar un alcance explícito.

**Impacto:** el objetivo de 80 % no cambia. Se define exactamente qué archivos cuentan como “lógica de negocio”, evitando que modelos y esquemas diluyan la métrica.

**Estado de implementación (17-11-2026):** implementado.

- `backend/pyproject.toml` configura `[tool.coverage.run] concurrency = ["greenlet"]` para medir el código que SQLAlchemy async ejecuta en greenlets.
- `scripts/nfr/coverage.sh` ejecuta el conjunto acordado, falla bajo 80 % y genera reporte de terminal, `coverage.xml` y HTML en `reports/nfr/coverage/`.
- Línea base con esta configuración: **95,65 % en el conjunto de la puerta**; todos los archivos superan 89 %.
- La puerta se integrará a CI en la fase de RNF-P-1.

### 3.15 RNF-M-2 — Observabilidad

**Ubicación:** §4, tabla “Mantenibilidad y calidad interna”, columna “Método de verificación”.

**Texto actual:**

> Guardado de Logs en la nube

**Texto propuesto:**

> Auditoría en `registro_auditoria` de acciones críticas (login/logout, cambios de estructura, entregas, revisiones, foro y descargas), logs JSON a stdout sin secretos, retención de IP a 90 días y de filas a 12 meses, y runbook para enviar los logs a CloudWatch o Loki en producción.

**Motivo:** no hay proveedor de logs en la nube configurado. La auditoría en base es la evidencia local verificable; el envío a la nube se documenta como paso de producción.

**Impacto:** el objetivo de observabilidad no cambia. Se explicita la diferencia entre auditoría en base, logs de aplicación y agregación en la nube.

**Estado de implementación (16-11-2026):** implementado el registro local.

- `registro_auditoria.ip` es nullable mediante la migración `d5f2a8c4e1b7`.
- `app/core/audit/service.py` agrega filas para login/logout, proyectos, hitos, entregables, entregas, revisiones, comentarios y descargas, y purga IP a 90 días y filas a 12 meses.
- `app/core/http.py` resuelve la IP con `X-Real-IP`/`X-Forwarded-For` cuando `TRUST_PROXY_HEADERS=true`.
- `app/core/logging.py` emite JSON a stdout; `backend/logging.json` configura Uvicorn con el mismo formateador, y las pruebas verifican que no se registren contraseñas ni tokens.
- `app/core/audit/purge.py` ejecuta la retención desde la línea de comandos.
- Pruebas en `backend/tests/test_nfr_observability.py`.
- El runbook de CloudWatch/Loki queda pendiente para la fase de operación.

### 3.16 RNF-P-1 — Entornos e infraestructura

**Ubicación:** §4, tabla “Portabilidad y despliegue”, columna “Método de verificación”.

**Texto actual:**

> Revisión del pipeline CI/CD

**Texto propuesto:**

> Pipeline de GitHub Actions con lint, tipos, tests, cobertura, build de imágenes Docker, smoke de Compose, E2E de Chromium y jobs NFR nightly/manual. Los artefactos de cobertura y reportes se publican en cada ejecución.

**Motivo:** el repositorio no tiene pipeline. La revisión documental no basta para verificar el despliegue en contenedores.

**Impacto:** el objetivo de Docker no cambia. Se agrega una obligación de mantener el pipeline verde.

**Estado de implementación (17-11-2026):** implementado.

- `.github/workflows/ci.yml` ejecuta backend quality, tests + cobertura, frontend y smoke de Docker en push a `main` y pull requests.
- `scripts/nfr/compose_smoke.sh` valida Compose, levanta `db`, `backend` y `web`, espera `/health/ready`, ejecuta el seed, comprueba la SPA y el login demo; `SMOKE_CLEANUP=1` elimina el stack.
- `README.md` y `spec/GuiaRepo.md` documentan los comandos y el pipeline.
- El despliegue automático al VPS no se incluye; el pipeline verifica el build y el runtime local.

## 4. Cambios en §10 — Criterios de aceptación y validación

### 4.1 Requisitos regulatorios de verificación

**Texto actual (resumen):**

- La política de privacidad está publicada y el consentimiento se registra con fecha y versión.
- Las funciones de exportación y eliminación de datos personales (RF-21) funcionan.
- Una prueba automatizada sobre el esquema confirma que no existen campos de RUT ni de calificaciones.
- El certificado TLS y la configuración de cifrado se revisan con una herramienta de análisis externa.
- Los entornos que no son de producción contienen solo datos sintéticos.

**Texto propuesto:**

> **Verificación regulatoria de esta fase.** Se mantienen las comprobaciones de esquema sin RUT/calificaciones, configuración TLS y datos sintéticos. Las comprobaciones de consentimiento (RF-19) y de exportación/supresión (RF-21) quedan fuera de esta fase porque esos requisitos funcionales no están implementados; se registran como brechas en el informe final. La auditoría TLS de producción con SSL Labs queda pendiente hasta contar con dominio y certificado.

**Motivo:** el SRS no debe declarar como verificadas funciones que no existen. Es preferible explicitar el alcance y la brecha antes que presentar una verificación incompleta como cumplimiento.

**Impacto:** §10 deja de ser una lista uniforme y pasa a distinguir entre verificaciones ejecutadas, pendientes y excluidas. Esto debe reflejarse también en la conclusión del informe final.

**Estado de implementación (16-11-2026):** la comprobación de esquema sin RUT ni calificaciones está implementada en `backend/tests/test_nfr_schema.py`, sobre metadatos SQLAlchemy y `information_schema`. TLS y datos sintéticos quedan pendientes; RF-19/RF-21 siguen excluidos.

### 4.2 Plan de validación con usuarios

**Texto actual:** ya define 3–5 profesores, tareas PA-1/PA-2/PA-5, ≥ 85 % sin ayuda y SUS ≥ 68.

**Texto propuesto:** agregar una referencia a los artefactos:

> El protocolo de tareas, el cuestionario SUS y la plantilla de resultados se encuentran en `docs/nfr/usability-protocol.md`, `docs/nfr/sus-form.md` y `docs/nfr/results-template.md`.

**Motivo:** hacer trazable el plan a instrumentos concretos sin cambiar los criterios.

**Impacto:** no cambia el objetivo ni el número de participantes.

## 5. Cambio propuesto en §11 — Trazabilidad

El §11 actual vincula necesidades, RF, RNF, casos de prueba TC-* y módulos. No existe una tabla específica de RNF → pruebas NFR. Se propone agregar una subsección:

> **§11.1 Trazabilidad de requisitos no funcionales.** La tabla vincula cada RNF con sus checks `NFR-TC-*`, la evidencia y el estado de verificación.

Propuesta de tabla:

| RNF | Checks | Evidencia | Estado |
|---|---|---|---|
| RNF-R-1 | NFR-TC-R-1.1 a R-1.4 | `navigation.json`, `upload.json`, `load.json` | Automatizado; VPS pendiente |
| RNF-R-2 | NFR-TC-R-2.1 a R-2.3 | `load.json`, `load.md` | Automatizado; VPS pendiente |
| RNF-R-3 | NFR-TC-R-3.1 a R-3.4 | `storage.json`, `docs/operations/storage.md` | Automatizado local; S3 pendiente |
| RNF-D-1 | NFR-TC-D-1.1, D-1.2 | `test_health.py` | Brecha aceptada |
| RNF-D-2 | NFR-TC-D-2.1 a D-2.3 | `backup.json`, `restore-drill.json` | Automatizado local |
| RNF-S-1 | NFR-TC-S-1.1 a S-1.6 | Pruebas pytest | Automatizado |
| RNF-S-2 | NFR-TC-S-2.1 a S-2.6 | Pruebas pytest + Playwright | Automatizado |
| RNF-S-3 | NFR-TC-S-3.1 a S-3.3 | `tls.json` + SSL Labs | Local automatizado; producción pendiente |
| RNF-U-1 | NFR-TC-U-1.1 a U-1.3 | `axe/*.json` + checklist | Automatizado parcial + manual |
| RNF-U-2 | NFR-TC-U-2.1 a U-2.4 | Reporte Playwright | Automatizado + manual |
| RNF-U-3 | NFR-TC-U-3.1 a U-3.3 | Planillas U-3 | Manual pendiente |
| RNF-C-1 | NFR-TC-C-1.1 a C-1.3 | Reporte Playwright + checklist | Automatizado parcial |
| RNF-C-2 | NFR-TC-C-2.1 a C-2.4 | Pruebas pytest | Automatizado |
| RNF-M-1 | NFR-TC-M-1.1 a M-1.3 | `coverage.xml`/HTML | Automatizado |
| RNF-M-2 | NFR-TC-M-2.1 a M-2.5 | Pruebas pytest + runbook | Automatizado local; nube pendiente |
| RNF-P-1 | NFR-TC-P-1.1 a P-1.4 | CI + smoke | Automatizado |

**Motivo:** el §11 actual no permite responder “¿dónde está la evidencia de este RNF?”. La tabla cierra esa brecha y conecta el SRS con `spec/nfr-test-plan.md`.

**Impacto:** agrega una subsección y no elimina la matriz existente.

## 6. Cambio propuesto en §10 — Definición de Terminado (DoD)

**Texto actual (DoD, §10):**

> Los RNF asociados en §3.2 se verificaron con el método indicado en §4 cuando corresponde (p. ej., tiempo de respuesta medido).

**Texto propuesto:**

> Los RNF asociados en §3.2 se verificaron con el método indicado en §4 y con los checks `NFR-TC-*` de §11.1. La cobertura de lógica de negocio se mide con `pytest-cov` y debe ser ≥ 80 %.

**Motivo:** la referencia actual es genérica; la nueva redacción conecta la definición de terminado con evidencia concreta.

**Impacto:** no cambia el criterio de aceptación; lo hace auditable.

## 7. Decisiones de alcance que deben quedar registradas

Estas decisiones no son cambios de tecnología, pero afectan lo que el SRS puede afirmar como verificado:

| Decisión | Efecto en `main.tex` |
|---|---|
| RNF-D-1 no se verifica automáticamente | Agregar “pendiente” en el método de verificación; no declarar 99,5 % como cumplido. |
| RF-19 y RF-21 no se implementan | Excluir las comprobaciones de consentimiento, exportación y supresión de §10; registrar la brecha. |
| §2.6 costo, schedule, extensibilidad e interoperabilidad | Mantener como restricciones del proyecto, pero no incluirlas en el plan NFR automatizado. |
| RNF-U-3 es manual | Mantener el objetivo y referenciar protocolo/plantillas. |
| RNF-C-1 usa motores equivalentes | Explicar que Edge≈Chromium y Safari≈WebKit; versiones penúltimas manuales. |
| RNF-C-2 no valida magic bytes | Documentar la limitación; no afirmar validación profunda de contenido. |
| RNF-S-3 solo tiene certificados autofirmados | Distinguir prueba local de auditoría de producción. |
| RNF-M-2 no tiene logs en la nube | Distinguir auditoría en base + logs JSON de la agregación cloud. |
| RNF-R-3 no tiene S3 ni ciclo de vida | Distinguir reporte local de la operación de objetos. |
| RNF-D-2 no tiene copia offsite | Distinguir respaldo local de la copia fuera del servidor. |

## 8. Procedimiento de aplicación futura

Cuando se autorice editar `main.tex`, aplicar en este orden:

1. Actualizar las filas de §4 con los textos propuestos de §3.
2. Actualizar §10 con la redacción de §4.1 y la referencia de §4.2.
3. Agregar §11.1 con la tabla de trazabilidad de §5.
4. Actualizar la frase del DoD en §10 con la redacción de §6.
5. Verificar que §2.6 y §9.1 no contradigan los nuevos métodos.
6. Compilar con pdfLaTeX y revisar que no queden referencias a JMeter, Lighthouse, SonarQube o Pingdom como herramientas obligatorias.
7. Revisar que las brechas de §7 estén declaradas en la conclusión del informe final.

## 9. Riesgos de no aplicar estos cambios

- El SRS seguiría exigiendo JMeter, Lighthouse y SonarQube, que no forman parte del stack ni del CI.
- RNF-S-1 seguiría sin una duración de bloqueo verificable.
- RNF-M-2 seguiría prometiendo logs en la nube que no existen.
- RNF-D-1 seguiría afirmando una disponibilidad sin evidencia.
- §10 seguiría incluyendo comprobaciones de RF-19/RF-21 no implementadas.
- La matriz de trazabilidad no permitiría ubicar la evidencia de cada RNF.

Este documento es la lista de cambios pendientes; no reemplaza la edición real de `main.tex`.

## 10. Registro de implementación

| Fecha | RNF | Estado | Cambios aplicados |
|---|---|---|---|
| 16-11-2026 | RNF-S-1 | Implementado | Configuración de bloqueo (5 intentos, 15 min), columnas `intentos_fallidos` y `bloqueado_hasta`, migración `7a1c3e5b9d2f`, lógica de bloqueo/expiración/reinicio y pruebas de hash Argon2id y ausencia de registro abierto. |
| 16-11-2026 | RNF-S-2 | Implementado en backend | Matriz rol × endpoint, inventario OpenAPI, pruebas de acceso anónimo/no participante/colaborador/gestor, inbox, historial y descargas en `backend/tests/test_nfr_rbac.py`. Quedan pruebas de componente y E2E. |
| 16-11-2026 | RNF-C-2 | Implementado | Matriz de formatos/MIME, tamaño, archivo vacío, enlace inválido y rechazo atómico en `backend/tests/test_nfr_uploads.py`. Sin magic bytes por decisión documentada. |
| 16-11-2026 | RNF-M-2 | Implementado localmente | Auditoría en `registro_auditoria` para acciones críticas, IP nullable, logs JSON, purga 90/365 días y pruebas en `backend/tests/test_nfr_observability.py`. Runbook CloudWatch/Loki pendiente. |
| 17-11-2026 | RNF-M-1 | Implementado | Cobertura con `concurrency = ["greenlet"]`, puerta de 80 % en `scripts/nfr/coverage.sh` y reportes XML/HTML en `reports/nfr/coverage/`. Línea base: 95,65 % en el conjunto de la puerta. |
| 17-11-2026 | RNF-P-1 | Implementado | GitHub Actions con backend, frontend, cobertura y smoke de Docker; `scripts/nfr/compose_smoke.sh`; README y GuiaRepo actualizados. |
| 17-11-2026 | RNF-S-3 | Implementado localmente | Perfil TLS autofirmado, `nginx.tls.conf`, `compose.tls.yaml`, `tls_check.py`, `tls_smoke.sh`, job CI `tls-handshake` y runbook. Certificado de producción/SSL Labs pendiente. |
| 17-11-2026 | RNF-R-3 | Implementado localmente | Reporte de bytes reales/registrados, cuota 100 GB, alerta 80 %, discrepancia 5 %, códigos 0/2/1, pruebas, runbook y job nightly. S3, ciclo de vida y AWS Budgets pendientes. |
| 17-11-2026 | RNF-D-2 | Implementado localmente | `backup.sh`, `restore_drill.sh`, manifiesto con SHA-256/conteos, retención 30 días, RPO 24 h/RTO 4 h medidos, reporte y job nightly. Copia offsite/cifrado pendientes. |
| 17-11-2026 | RNF-U-1 | Implementado parcialmente | axe-core en Chromium sobre las páginas principales, pruebas de teclado/foco y checklist manual creada. La ejecución del checklist y la conformidad completa quedan pendientes. |
| 17-11-2026 | RNF-U-2 | Implementado en Chromium | PA-1, PA-2 y PA-5 a 360×800 sin scroll horizontal; dispositivos físicos pendientes. |
| 17-11-2026 | RNF-C-1 | Implementado parcialmente | Proyectos Playwright Chromium/Firefox/WebKit; Chromium y Firefox locales, WebKit en CI; versiones penúltimas manuales pendientes. |
| 17-11-2026 | RNF-U-3 | Artefactos creados; ejecución pendiente | Protocolo, cuestionario SUS y plantilla de resultados en `docs/nfr/`. No hay sesiones con profesores todavía. |
| 17-11-2026 | RNF-R-1 | Implementado localmente; VPS pendiente | Playwright mide navegación y subida de 10 MB; `navigation.json` y umbrales aplicables con `E2E_PERF_ENFORCE=1`. |
| 17-11-2026 | RNF-R-2 | Implementado localmente; VPS pendiente | Seed SRS completo, load test 100 usuarios/15 min, reporte de memoria y jobs nightly/VPS. Smoke local verificado. |
| 16-11-2026 | §10 REG-1 | Implementado | Prueba de ausencia de columnas/tablas de RUT y calificaciones en `backend/tests/test_nfr_schema.py`. |
| 16-11-2026 | RNF-S-1/S-2/S-3/C-1/C-2/D-2/M-1/M-2/P-1/R-1/R-2/R-3/U-1/U-2/U-3 | Pendiente de SRS | Los textos de §4 y §10 siguen sin editarse en `main.tex`; este archivo conserva la propuesta. |
