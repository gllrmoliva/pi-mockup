# Plan de verificación de requisitos no funcionales — Hito

**Versión:** 1.1  
**Fecha:** 17 de noviembre de 2026  
**Fuente de requisitos:** `spec/main.tex`, §4 y §10  
**Documento hermano:** `spec/main-tex-nfr-changes.md`  
**Estado:** aprobado para implementación

## 1. Propósito

Este documento define cómo se verificará cada requisito no funcional (RNF) del SRS de *Hito*. Incluye el alcance, las decisiones de implementación, los casos de prueba, las herramientas, los datos sintéticos, la integración continua, la evidencia esperada y las brechas que quedarán explícitas.

El plan cubre los RNF de §4 y las verificaciones de §10 que comprueban directamente un RNF. No cubre las restricciones de §2.6 que dependen de presupuesto, calendario, extensibilidad o interoperabilidad, salvo que se indique lo contrario.

## 2. Decisiones de alcance

| Decisión | Regla adoptada |
|---|---|
| Alcance | RNF de §4 y verificaciones de §10 que comprueban directamente un RNF. |
| Comportamiento faltante | Se implementa, no solo se prueba: bloqueo de login, auditoría, TLS, respaldo/restauración, alerta de almacenamiento y cobertura de 80 %. |
| Navegador y accesibilidad | Playwright + `@axe-core/playwright`. |
| Carga y rendimiento | Generador asíncrono en Python con `httpx`; sin JMeter ni Lighthouse como herramientas obligatorias. |
| Cobertura | `pytest-cov`, umbral de 80 % sobre la lógica de negocio definida en §7. |
| CI/CD | GitHub Actions; pruebas rápidas en cada PR y matriz completa en nightly/manual. |
| Rendimiento en CI | Reporte sin bloqueo en runners locales; bloqueo en el VPS cuando exista. |
| Navegadores | Chromium en PR; Chromium, Firefox y WebKit en nightly/manual. |
| TLS | Perfil local con certificados autofirmados; certificado de producción y SSL Labs quedan como runbook pendiente. |
| Disponibilidad | RNF-D-1 no se verifica automáticamente por decisión del equipo; se registra como brecha. |
| Datos personales | RF-19 y RF-21 no se verifican; se registran como brechas de §10. |
| Auditoría | Códigos de acción en español; limpieza de IP a 90 días y de filas a 12 meses. |
| Archivos de revisión | Se adjuntan solo al registrar la revisión, usan los formatos y tamaño del entregable, no crean una nueva versión de entrega y se incluyen en la validación de formatos y en la matriz de descargas. |
| Usabilidad | RNF-U-3 es manual; se entregan protocolo, cuestionario SUS y plantillas de resultados. |
| Documentación | `main.tex` no se modifica. Todos los cambios propuestos se listan en `spec/main-tex-nfr-changes.md`. |

## 3. Niveles de prueba y entornos

### 3.1 Niveles

| Nivel | Qué prueba | Dónde corre | Frecuencia |
|---|---|---|---|
| L1 | Unitarias e integración rápida de backend y frontend | Local y CI | Cada PR |
| L2 | Integración de seguridad, RBAC, cargas, auditoría y esquema | Local y CI | Cada PR |
| L3 | E2E de navegador, accesibilidad y 360 px | Local y CI | Chromium en PR; todos los motores en nightly |
| L4 | Rendimiento, respaldo/restauración, TLS y almacenamiento | Local, CI nightly y VPS | Nightly/manual; VPS cuando esté disponible |
| L5 | Validación con usuarios, WCAG manual, navegadores penúltimos y SSL Labs | Presencial/remoto y VPS | Manual, según §10 |

### 3.2 Entornos

| Entorno | Uso | Configuración |
|---|---|---|
| Local | Desarrollo y pruebas funcionales | Docker Compose, base `hito_test` y `hito_e2e` |
| CI | Regresión y NFR automatizables | GitHub Actions, PostgreSQL como servicio o Compose |
| VPS | Evidencia de producción | Docker Compose, dominio, TLS de producción y monitoreo externo |
| Rendimiento | Dataset completo | Base `hito_perf`, datos sintéticos y archivos dispersos |

Ningún entorno de prueba recibe datos reales. Los datos de `hito_e2e` y `hito_perf` son sintéticos.

## 4. Matriz resumen RNF → verificación

| RNF | Objetivo del SRS | Verificación principal | Nivel | Estado esperado |
|---|---|---|---|---|
| RNF-R-1 | p95 ≤ 500 ms en navegación y ≤ 3 s en subida | Playwright: tiempos de navegación y subida | L4/VPS | Automatizado |
| RNF-R-2 | 100 usuarios concurrentes 15 min, p95 de R-1 y error < 1 % | Generador asíncrono con dataset completo | L4/VPS | Automatizado |
| RNF-R-3 | 33–66 GB/año, hasta 100 GB, sin superar USD 10/mes | Reporte de almacenamiento y alerta al 80 % | L2/L4 | Automatizado local; costo documentado |
| RNF-D-1 | ≥ 99,5 % mensual | Sin verificación automática | — | Brecha aceptada |
| RNF-D-2 | RPO 24 h / RTO 4 h | Respaldo y simulacro de restauración | L4 | Automatizado |
| RNF-S-1 | Hash de contraseñas, bloqueo tras 5 fallos, sin registro abierto | Pruebas de esquema, bloqueo y rutas | L2 | Automatizado |
| RNF-S-2 | RBAC estricto por rol de proyecto | Matriz rol × endpoint y E2E | L2/L3 | Automatizado |
| RNF-S-3 | TLS 1.2+ en tránsito | Configuración estática y handshake autofirmado | L2/L4 | Automatizado local; producción pendiente |
| RNF-U-1 | WCAG 2.1 AA | axe-core, teclado y checklist manual | L3/L5 | Automatizado parcial + manual |
| RNF-U-2 | 100 % de PA-1, PA-2 y PA-5 a 360 px sin scroll horizontal | Playwright a 360×800 | L3 | Automatizado |
| RNF-U-3 | ≥ 85 % de tareas sin ayuda y SUS ≥ 68 | Protocolo manual con 3–5 profesores | L5 | Manual |
| RNF-C-1 | Chrome, Firefox, Safari y Edge; última y penúltima | Smoke en Chromium, Firefox y WebKit | L3/L5 | Automatizado parcial + manual |
| RNF-C-2 | Validación estricta por extensión y MIME | Matriz de subida y archivos de revisión | L2 | Automatizado |
| RNF-M-1 | ≥ 80 % en lógica de negocio | `pytest-cov` con umbral | L2 | Automatizado |
| RNF-M-2 | Logs centralizados de acciones críticas | Auditoría, JSON logs y retención | L2/L4 | Automatizado local; nube documentada |
| RNF-P-1 | Despliegue en contenedores Docker | Compose, build, health y smoke | L2 | Automatizado |

## 5. Casos de prueba por RNF

### RNF-R-1 — Tiempo de respuesta p95

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-R-1.1 | Playwright carga `/`, `/projects/{id}` y `/deliverables/{id}`; 10 muestras por página. Medir desde el inicio de la navegación hasta que el contenido objetivo esté visible. | p95 ≤ 500 ms por página, en el VPS con Nginx y datos completos. | `reports/nfr/navigation.json` | L4/VPS |
| NFR-TC-R-1.2 | Subir un PDF de 10 MB desde la interfaz; 3 muestras. Medir desde el clic de envío hasta la confirmación de éxito. | p95 ≤ 3 s. | `reports/nfr/navigation.json` | L4/VPS |
| NFR-TC-R-1.3 | Ejecutar el mismo conjunto contra el entorno local. | Reporte informativo; no bloquea el PR. | JSON con entorno, commit y percentiles | L4 |
| NFR-TC-R-1.4 | Medir p50, p95 y p99 por endpoint en el generador de carga. | p95 ≤ 500 ms para endpoints de lectura. | `reports/nfr/load.json` | L4 |

Notas:

- La medición usa `page.goto` y espera a que el encabezado objetivo sea visible; no usa marcas manuales de `performance` ni `PerformanceNavigationTiming`.
- Lighthouse no se usa como herramienta obligatoria. La justificación y el cambio propuesto al SRS están en `spec/main-tex-nfr-changes.md`.
- Los umbrales se bloquean en el VPS. En GitHub Actions solo se reportan.

### RNF-R-2 — Concurrencia de usuarios

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-R-2.1 | Generador asíncrono: 100 usuarios virtuales, 15 minutos, 30 s de rampa. Cada usuario inicia sesión una vez y reutiliza su cookie. Mezcla: 35 % `GET /projects`, 20 % `GET /projects/{id}`, 15 % `GET /deliverables/{id}`, 10 % `GET /reviews/pending`, 15 % descarga de archivo, 5 % escrituras (3 % mensaje de foro, 1 % entrega por enlace, 1 % revisión sin archivos). Las revisiones se envían como form data con `decision`; no usan JSON. | p95 de R-1 y tasa de error < 1 %. Se cuentan como error las respuestas 5xx, los fallos de transporte y los 4xx inesperados. | `reports/nfr/load.json` y `load.md` | L4/VPS |
| NFR-TC-R-2.2 | Smoke de carga en CI: 10 usuarios, 30 s, misma mezcla. | Reporte sin bloqueo. | JSON de CI | L4 |
| NFR-TC-R-2.3 | Ejecución contra el VPS con `--enforce`. | Falla si no se cumplen p95 o tasa de error. | JSON + salida de CI | L4/VPS |
| NFR-TC-R-2.4 | Muestrear `docker stats` de `backend`, `db` y `web` durante la carga, excluyendo el generador. | Reporta pico/medio de RAM e instancia AWS sugerida; sirve para estimar el costo de §2.6. | `reports/nfr/memory.json` | L4 |

Reglas del generador:

- Los usuarios virtuales comparten el dataset SRS; las escrituras usan entregables abiertos o enviados y toleran 409 por carreras.
- Las revisiones de carga se envían como `form data` con `decision` y sin archivos; el endpoint dejó de aceptar JSON al incorporar archivos opcionales.
- El reporte incluye percentiles por endpoint, códigos de respuesta, throughput y errores.
- La semilla de rendimiento es reiniciable con `PERF_CLEANUP=1` o `compose down -v`.
- La RAM se muestrea con `docker stats` y se agrega a `load.json`; el generador de carga queda excluido del pico.

### RNF-R-3 — Volumen de datos y crecimiento

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-R-3.1 | `storage_report.py` suma el tamaño real de los archivos del volumen de subidas y el tamaño reportado en `archivo.tamano`. Compara con `STORAGE_QUOTA_GB=100`. | WARN al 80 %; fallo al 100 %. Si la diferencia entre bytes reales y metadatos supera 5 %, se reporta inconsistencia. | `reports/nfr/storage.json` | L2/L4 |
| NFR-TC-R-3.2 | Reporte de crecimiento por año a partir de `created_at` y `archivo.tamano`. | El escenario sintético debe caer en el rango 33–66 GB/año y ≤ 100 GB almacenados. | `storage.json` | L4 |
| NFR-TC-R-3.3 | Pruebas unitarias del reporte con directorios temporales, archivos dispersos y cuotas simuladas. | Umbrales y códigos de salida correctos. | Prueba pytest | L2 |
| NFR-TC-R-3.4 | Runbook de S3, ciclo de vida y alerta de presupuesto de AWS. | Documentado; no automatizado en este repositorio. | `docs/operations/storage.md` | L5 |

El reporte suma todas las filas de `archivo`, incluidas las asociadas a revisiones, y el volumen de subidas incluye sus archivos. La retención de 12 meses posterior al cierre del proyecto no está implementada porque el cierre de proyecto no forma parte del alcance actual. El reporte debe indicar esa dependencia: sin retención, el almacenamiento no se estabiliza en 100 GB. Se registra como brecha.

### RNF-D-1 — Disponibilidad

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-D-1.1 | Pruebas existentes de `/health/live` y `/health/ready`. | Ambos endpoints responden correctamente. | `backend/tests/test_health.py` | L1 |
| NFR-TC-D-1.2 | Verificación de disponibilidad mensual ≥ 99,5 %. | **No se ejecuta.** Requiere un monitor externo (Pingdom o equivalente) y un mes de datos. | Brecha documentada | — |

Decisión: RNF-D-1 no se verifica automáticamente en esta fase. El SRS mantiene el objetivo, pero la evidencia de disponibilidad queda pendiente y no se puede afirmar su cumplimiento.

### RNF-D-2 — RPO / RTO

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-D-2.1 | `backup.sh` ejecuta `pg_dump -Fc` y un archivo `tar --sparse` de las subidas. Genera manifiesto con fecha, tamaño, SHA-256, conteos y cantidad de archivos. | Respaldo diario; retención local de 30 días; el respaldo más reciente tiene ≤ 24 h. | `backups/manifest-*.json` | L4 |
| NFR-TC-D-2.2 | `restore_drill.sh` verifica los SHA-256, restaura en una base y un directorio desechables, compara conteos de tablas y cantidad de archivos, y mide el tiempo total. | Restauración íntegra y RTO ≤ 4 h. | `reports/nfr/restore-drill.json` | L4 |
| NFR-TC-D-2.3 | Programación diaria documentada (cron o systemd timer) y procedimiento de restauración. | Runbook completo. | `docs/operations/backup-restore.md` | L5 |

Alcance actual: respaldos locales. El dump de PostgreSQL incluye todas las filas de `archivo`, tanto de entregas como de revisiones, y el `tar` incluye sus archivos físicos. La copia fuera del servidor (S3 u otro) y el cifrado en reposo quedan documentados como pendientes de producción.

### RNF-S-1 — Autenticación

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-S-1.1 | Consultar todas las filas de `usuario` y verificar el prefijo del hash. | 100 % de las credenciales usan Argon2id (`$argon2id$`); ninguna contraseña en texto plano. | Prueba pytest | L2 |
| NFR-TC-S-1.2 | Intentar iniciar sesión con contraseña incorrecta 5 veces; en el sexto intento usar la contraseña correcta. Repetir después de vencer el bloqueo. | Quinto fallo deja la cuenta bloqueada; el sexto intento responde 423 con mensaje explícito; tras 15 min la cuenta vuelve a permitir el acceso. | Prueba pytest | L2 |
| NFR-TC-S-1.3 | Iniciar sesión correctamente después de fallos previos. | El contador de fallos se reinicia. | Prueba pytest | L2 |
| NFR-TC-S-1.4 | Intentar con un correo inexistente. | 401 genérico; no se crea bloqueo para una cuenta inexistente. | Prueba pytest | L2 |
| NFR-TC-S-1.5 | Inspeccionar el inventario de rutas OpenAPI y la pantalla de login. | No existe `/register`, `/signup`, `/auth/register` ni enlace “Crear cuenta”/“Registrarse”; no hay OAuth. | Prueba backend + frontend | L2 |
| NFR-TC-S-1.6 | Iniciar sesión y revisar la cookie y la tabla `sesion`. | Cookie `HttpOnly`, `SameSite=Lax`, `Secure` cuando `SESSION_COOKIE_SECURE=true`; token de sesión almacenado como hash. | Prueba pytest | L2 |

Parámetros por defecto:

- `MAX_FAILED_LOGIN_ATTEMPTS=5`
- `LOGIN_LOCKOUT_MINUTES=15`
- Respuesta: HTTP 423 con `"Cuenta bloqueada temporalmente. Intente nuevamente en 15 minutos."`
- Un login exitoso reinicia el contador.
- Los correos inexistentes no se bloquean.

### RNF-S-2 — Autorización y privacidad

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-S-2.1 | Inventario de operaciones OpenAPI contra un mapa de acceso mantenido en la prueba. | Toda ruta nueva debe declarar su nivel de acceso; la prueba falla si una ruta no está en el mapa. | Prueba pytest | L2 |
| NFR-TC-S-2.2 | Matriz parametrizada rol × endpoint: anónimo, no participante, colaborador, gestor y otro gestor. | 401 para anónimo; 404 para no participante; 403 para rol incorrecto; 200/201 para rol permitido. | Prueba pytest | L2 |
| NFR-TC-S-2.3 | Descargar una versión antigua y los archivos de una revisión antigua como colaborador y como gestor; descargar como no participante. | Gestor ve todas las versiones y archivos de revisión; colaborador solo la última entrega y los archivos de la revisión de esa última entrega (403 en versiones y revisiones antiguas); no participante 404. | `test_nfr_review_files.py` | L2 |
| NFR-TC-S-2.4 | Revisar la interfaz como colaborador: acciones de gestor, ruta de historial y botones de revisión. | La interfaz no muestra acciones de gestor; la ruta de historial queda bloqueada. | Prueba de componente + E2E | L2/L3 |
| NFR-TC-S-2.5 | PA-4: un estudiante abre por URL un proyecto ajeno. | El sistema lo impide y no filtra datos. | Playwright | L3 |
| NFR-TC-S-2.6 | Listar proyectos e inbox de revisión con varios usuarios. | Cada usuario ve solo sus proyectos y sus revisiones pendientes. | Prueba pytest | L2 |

La matriz completa de endpoints y roles está en el Anexo B.

### RNF-S-3 — Protección de datos en tránsito

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-S-3.1 | Revisar la configuración TLS del perfil `compose.tls.yaml`. | Solo TLS 1.2 y 1.3; HSTS; redirección HTTP→HTTPS; cookie segura. | Prueba estática | L2 |
| NFR-TC-S-3.2 | Generar certificados autofirmados y levantar el perfil TLS. Realizar handshakes con Python `ssl`/OpenSSL. | TLS 1.2 y 1.3 aceptados; TLS 1.0 y 1.1 rechazados; la aplicación responde por HTTPS. | `reports/nfr/tls.json` | L2/L4 |
| NFR-TC-S-3.3 | Ejecutar SSL Labs contra el dominio de producción. | Calificación y protocolos aceptables; certificado válido y renovación documentada. | Captura/informe manual | L5 |

Alcance actual: certificados autofirmados para pruebas locales. El certificado de producción, Certbot y SSL Labs quedan documentados y pendientes. El objetivo del SRS no cambia; la evidencia de producción no está disponible todavía.

### RNF-U-1 — Accesibilidad

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-U-1.1 | Ejecutar axe-core con etiquetas `wcag2a`, `wcag2aa`, `wcag21a` y `wcag21aa` en login, portafolio, detalle de proyecto, formulario de proyecto, detalle de entregable, historial y 404, en Chromium. Firefox y WebKit se cubren con el smoke funcional. | Cero violaciones. Si aparece una excepción, debe estar justificada y con fecha de caducidad. | `reports/nfr/playwright/` | L3 |
| NFR-TC-U-1.2 | Pruebas de teclado: skip link, orden de tabulación, foco visible, trampa de foco en diálogos, Escape, retorno de foco, etiquetas y `aria-live`. | Todos los flujos son operables por teclado y el foco es predecible. | `frontend/e2e/keyboard.spec.ts` | L3 |
| NFR-TC-U-1.3 | Checklist manual WCAG 2.1 AA para lo que axe no cubre: lector de pantalla, zoom 200 %, contraste, movimiento reducido, identificación de errores. | Checklist completo y hallazgos corregidos o registrados. | `docs/nfr/wcag-manual-checklist.md` | L5 |

axe-core no demuestra por sí solo conformidad WCAG 2.1 AA. La verificación automática es un subconjunto; el checklist manual es obligatorio para afirmar cumplimiento.

### RNF-U-2 — Diseño responsivo

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-U-2.1 | Playwright con viewport 360×800 recorre portafolio, formulario, proyecto, entregable, historial, bandeja y diálogos. Verificar `document.documentElement.scrollWidth <= window.innerWidth` y que ningún elemento exceda el ancho en más de 1 px. | Sin desplazamiento horizontal en las páginas y diálogos cubiertos. | Reporte Playwright | L3 |
| NFR-TC-U-2.2 | Ejecutar PA-1, PA-2 y PA-5 completos a 360 px en Chromium. | Las tres tareas se completan sin scroll horizontal. | `frontend/e2e/responsive.spec.ts` | L3 |
| NFR-TC-U-2.3 | Emulación de dispositivos móviles Pixel/iPhone. | Pendiente; se documenta la limitación de la emulación. | Manual | L3 |
| NFR-TC-U-2.4 | Verificación en dispositivos físicos iOS/Android. | Pendiente; se documenta la limitación de la emulación. | Manual | L5 |

PA-5 incluye el objetivo de “menos de 30 segundos y sin ayuda”. La parte de 30 segundos se puede medir en la prueba automatizada; “sin ayuda” se valida en RNF-U-3.

### RNF-U-3 — Facilidad de uso sin capacitación

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-U-3.1 | Sesión de 20–30 min con 3–5 profesores guía. Tareas PA-1, PA-2 y PA-5 sin ayuda; registro de éxito, tiempo, errores y ayudas. | ≥ 85 % de las tareas completadas sin ayuda en el primer intento. | Planilla de resultados | L5 |
| NFR-TC-U-3.2 | Aplicar el cuestionario SUS de 10 preguntas al finalizar. | Puntaje SUS ≥ 68. | Planilla SUS | L5 |
| NFR-TC-U-3.3 | Documentar consentimiento, códigos de participante y resultados agregados. | Sin datos personales en el repositorio. | Anexo B/H de `main.tex` | L5 |

Artefactos creados:

- `docs/nfr/usability-protocol.md`
- `docs/nfr/sus-form.md`
- `docs/nfr/results-template.md`

La prueba automatizada PA-1/PA-2/PA-5 es un proxy de regresión, no sustituye el estudio con usuarios.

### RNF-C-1 — Navegadores soportados

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-C-1.1 | Smoke Playwright en Chromium, Firefox y WebKit: login, portafolio, detalle de proyecto, detalle de entregable, subida, revisión y foro. | Todos los flujos pasan en los tres motores. | `reports/nfr/playwright/` | L3 |
| NFR-TC-C-1.2 | Ejecutar Chromium en cada PR; Firefox y WebKit en nightly/manual. | Chromium bloquea el PR; los otros motores bloquean el nightly. | CI | L3 |
| NFR-TC-C-1.3 | Checklist manual de versiones penúltimas de Chrome, Edge, Firefox y Safari. | Documentado en cada release. | `docs/nfr/browser-matrix.md` | L5 |

Limitaciones:

- Edge usa el motor Chromium; no se prueba el binario Edge.
- Safari se aproxima con WebKit; no es Safari real.
- Playwright instala una versión concreta por motor; las versiones penúltimas se revisan manualmente.
- No se usan APIs experimentales; se revisa en código y se mantiene un `browserslist`/target de build conservador.

### RNF-C-2 — Formatos de archivo

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-C-2.1 | Subir PDF, ZIP y DOCX con sus MIME permitidos; extensiones en mayúsculas; varios archivos; archivo + enlace; solo enlace. | Todas las combinaciones válidas se aceptan y se registran con MIME y SHA-256. | Prueba pytest | L2 |
| NFR-TC-C-2.2 | Adjuntar PDF, ZIP y DOCX a una revisión; probar un archivo y varios archivos. | Todos los formatos admitidos se aceptan, quedan asociados a la revisión y no crean una nueva versión de entrega. | Prueba pytest | L2 |
| NFR-TC-C-2.3 | Subir extensión no permitida, MIME incorrecto, MIME ausente, nombre ausente, archivo de 0 bytes y archivo sobre el tamaño máximo en una entrega. | Todas se rechazan con 422 y mensaje claro. | Prueba pytest | L2 |
| NFR-TC-C-2.4 | Adjuntar a una revisión extensión no permitida, MIME incorrecto, MIME ausente, nombre ausente, archivo de 0 bytes y archivo sobre el tamaño máximo. | Todas se rechazan con 422; la revisión no se crea. | Prueba pytest | L2 |
| NFR-TC-C-2.5 | Enviar una entrega con un archivo válido y uno inválido. | Se rechaza la entrega completa; no quedan filas ni archivos parciales. | Prueba pytest | L2 |
| NFR-TC-C-2.6 | Registrar una revisión con un archivo válido y uno inválido. | Se rechaza la revisión completa; no quedan revisión, filas de archivo ni archivos almacenados. | Prueba pytest | L2 |
| NFR-TC-C-2.7 | Verificar metadatos de archivos aceptados en entregas y revisiones. | `tipo_mime`, `tamano` y hash SHA-256 coinciden; el archivo se almacena fuera de PostgreSQL. | Prueba pytest | L2 |

Los casos de revisión se implementan en `backend/tests/test_nfr_review_files.py` y se ejecutan con `pytest -m nfr`.

Limitación: se valida la extensión y el MIME declarado por el cliente, no los magic bytes, tanto en entregas como en archivos de revisión. Un archivo malicioso puede declarar un MIME permitido. Se documenta como brecha; un endurecimiento futuro puede usar `python-magic`.

### RNF-M-1 — Cobertura de pruebas

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-M-1.1 | Ejecutar `pytest` con `pytest-cov` sobre el conjunto de lógica de negocio. | Cobertura de línea ≥ 80 %. Se reporta cobertura de ramas como métrica complementaria. | `coverage.xml` y HTML | L2 |
| NFR-TC-M-1.2 | Revisar el reporte por archivo. | Ningún archivo del conjunto queda en 0 %; los servicios principales superan el umbral global. | Reporte HTML | L2 |
| NFR-TC-M-1.3 | Ejecutar la puerta en CI. | El PR falla si la cobertura baja de 80 %. | Job de CI | L2 |

Conjunto exacto de archivos:

- `app/modules/auth/security.py`
- `app/modules/auth/service.py`
- `app/modules/deliverables/dependencies.py`
- `app/modules/deliverables/service.py`
- `app/modules/projects/dependencies.py`
- `app/modules/projects/service.py`
- `app/modules/storage/service.py`
- `app/api/deps.py`
- `app/core/errors.py`
- `app/core/audit/service.py` (nuevo)

Excluidos: modelos, esquemas, routers, enums, `seed.py`, migraciones y `__init__.py`.

Línea base medida con `[tool.coverage.run] concurrency = ["greenlet"]`: **95,70 % en el conjunto de la puerta** y 90 % sobre toda la app. Los archivos del conjunto quedan entre 89,32 % y 100 % (`auth/service.py` 93,75 %, `deliverables/dependencies.py` 89,32 %, `deliverables/service.py` 97,28 %, `projects/service.py` 96,89 %, `storage/service.py` 94,29 %, `api/deps.py` 100 %, `core/audit/service.py` 100 %). La medición sin `greenlet` subestimaba el código ejecutado por SQLAlchemy async y no se usa.

La puerta es `scripts/nfr/coverage.sh`: ejecuta el conjunto, falla bajo 80 % y genera `coverage.xml` y HTML en `reports/nfr/coverage/`.

### RNF-M-2 — Observabilidad

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-M-2.1 | Ejecutar cada acción auditada y consultar `registro_auditoria`. | Existe una fila con usuario, acción, entidad, `entidad_id`, IP y fecha. | Prueba pytest | L2 |
| NFR-TC-M-2.2 | Revisar los logs de las acciones críticas. | No aparecen contraseñas, tokens, contenidos de archivos ni cuerpos completos de request. | Prueba pytest con `caplog`/`capsys` | L2 |
| NFR-TC-M-2.3 | Validar el formato JSON de los logs. | Cada línea es JSON válido con timestamp, nivel, logger y mensaje; las excepciones se registran sin datos sensibles. | Prueba pytest | L2 |
| NFR-TC-M-2.4 | Ejecutar `purge_audit.py` con fechas simuladas. | IP se vuelve `NULL` a los 90 días; filas se eliminan a los 12 meses. | Prueba pytest | L2 |
| NFR-TC-M-2.5 | Revisar el runbook de logs centralizados. | Local: stdout JSON. Producción: CloudWatch o Loki/Promtail documentado. | `docs/operations/logging.md` | L5 |

Acciones auditadas:

| Código | Entidad | Cuándo |
|---|---|---|
| `sesion.iniciar` | `sesion` | Login exitoso |
| `sesion.cerrar` | `sesion` | Logout |
| `proyecto.crear` | `proyecto` | Creación de proyecto |
| `proyecto.editar` | `proyecto` | Edición de proyecto y participantes |
| `hito.crear` | `hito` | Creación de hito |
| `entregable.crear` | `entregable` | Creación de entregable |
| `entregable.editar` | `entregable` | Edición de entregable |
| `entrega.crear` | `entrega` | Nueva versión de entrega |
| `revision.crear` | `revision` | Decisión de revisión |
| `comentario.crear` | `comentario` | Mensaje de foro |
| `archivo.descargar` | `archivo` | Descarga de archivo |

Los archivos adjuntos a una revisión se auditan dentro de `revision.crear`; sus descargas usan `archivo.descargar`. No se agrega una acción nueva. No se auditan los intentos de login fallidos por decisión de alcance. La tabla requiere que `ip` sea nullable para poder eliminarla a los 90 días.

### RNF-P-1 — Entornos e infraestructura

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-P-1.1 | Ejecutar `docker compose config`. | Configuración válida, sin secretos embebidos. | Salida de CI | L2 |
| NFR-TC-P-1.2 | Construir las imágenes de backend y frontend. | Builds exitosos y reproducibles. | Log de CI | L2 |
| NFR-TC-P-1.3 | Levantar `db`, `backend` y `web`; esperar healthchecks; iniciar sesión y listar proyectos. | Stack completo funcional. | `scripts/nfr/compose_smoke.sh` | L2 |
| NFR-TC-P-1.4 | Revisar el workflow de GitHub Actions. | CI/CD versionado y ejecutable en cada PR. | `.github/workflows/ci.yml` | L2 |

## 6. Verificaciones de §10

| ID | Procedimiento | Criterio | Evidencia | Nivel |
|---|---|---|---|---|
| NFR-TC-REG-1 | Inspeccionar metadatos SQLAlchemy y `information_schema.columns`. | No existen columnas `rut`, `run`, `nota`, `calificacion` ni `grade`; no hay tablas de calificaciones oficiales. | Prueba pytest | L2 |
| NFR-TC-REG-2 | Revisar configuración TLS y ejecutar handshake/SSL Labs. | TLS 1.2+ y certificado válido en producción. | `tls.json` + informe SSL Labs | L2/L5 |
| NFR-TC-REG-3 | Verificar que los scripts de seed y pruebas rechacen `APP_ENV=production`. | Ningún entorno no productivo recibe datos reales; los seeds son sintéticos. | Prueba pytest | L2 |
| NFR-TC-REG-4 | Verificar consentimiento, exportación y supresión de datos (RF-19/RF-21). | **Excluido.** RF-19 y RF-21 no están implementados. | Brecha documentada | — |

## 7. Datos sintéticos

### 7.1 E2E

- Base `hito_e2e`.
- Seed determinista con 7 usuarios, 4 proyectos y 7 entregables de ejemplo (seed actual) o un seed E2E equivalente.
- Cada ejecución reinicia la base y el volumen de subidas.
- Los tests crean datos propios con correos únicos cuando necesitan aislamiento.

### 7.2 Rendimiento

- Base `hito_perf`.
- 529 proyectos (265 activos y 264 cerrados), 5.290 entregables, 13.200 entregas y 6.600 archivos dispersos de 5–10 MB.
- Tamaño aparente: 33–66 GB; el espacio real en disco se reduce con archivos dispersos.
- 675 cuentas: 146 profesores y 529 estudiantes.
- El seed se niega a ejecutarse si `APP_ENV=production` o si el nombre de la base no contiene `perf`.
- Los archivos se generan con `truncate`/`ftruncate` para no ocupar el tamaño aparente.
- El respaldo usa `tar --sparse` para conservar la dispersión.

### 7.3 Privacidad

- Nombres, correos y temas son ficticios.
- No se usan datos de profesores o estudiantes reales.
- Los reportes no incluyen correos ni nombres; solo IDs y métricas.

## 8. Herramientas y comandos

### 8.1 Backend

```bash
# Suite rápida existente
docker compose --profile test run --rm backend-test

# Cobertura con umbral
scripts/nfr/coverage.sh

# Pruebas NFR de seguridad, RBAC, uploads, auditoría y esquema
docker compose --profile test run --rm --entrypoint /bin/sh backend-test \
  -c "alembic upgrade head && pytest tests -m nfr"
```

### 8.2 Frontend y E2E

```bash
cd frontend
npm ci
npx playwright install --with-deps

# Chromium, PR
npm run test:e2e -- --project=chromium

# Matriz completa, nightly
npm run test:e2e

# Solo accesibilidad o responsive
npm run test:e2e -- --project=chromium --grep @a11y
npm run test:e2e -- --project=chromium --grep @responsive
```

### 8.3 Rendimiento y almacenamiento

```bash
# Stack de rendimiento completo, carga, navegación y memoria
PERF_CLEANUP=1 ./scripts/nfr/perf.sh

# Smoke local
PERF_USERS=10 PERF_DURATION=30 PERF_RAMP_UP=5 PERF_CLEANUP=1 ./scripts/nfr/perf.sh

# Carga directa contra un VPS
PERF_PASSWORD=... python scripts/nfr/load_test.py \
  --base-url https://tu-dominio \
  --users 100 \
  --duration 900 \
  --report reports/nfr/load-vps.json \
  --enforce

./scripts/nfr/storage_report.sh \
  --quota-gb 100 \
  --alert-percent 80
```

`perf.sh` escribe `reports/nfr/load.json`, `load.md`, `navigation.json` y `memory.json`. El wrapper de almacenamiento escribe `reports/nfr/storage.json` y devuelve `0` (ok), `2` (warning) o `1` (crítico).

### 8.4 TLS, respaldo y smoke

```bash
docker compose -f compose.yaml -f compose.tls.yaml up -d
python scripts/nfr/tls_check.py --host localhost --port 8443

scripts/nfr/backup.sh
scripts/nfr/restore_drill.sh

scripts/nfr/compose_smoke.sh
```

## 9. Integración continua

### 9.1 `ci.yml` — cada push y PR

| Job | Contenido |
|---|---|
| `backend-quality` | `ruff check`, `ruff format --check`, `pyright` |
| `backend-tests` | PostgreSQL, migraciones, `pytest` con cobertura ≥ 80 % |
| `frontend-quality` | `npm run lint`, `npm run typecheck`, `npm run test:run`, `npm run build` |
| `docker-smoke` | `docker compose config`, build, healthchecks, login |
| `e2e-chromium` | Playwright Chromium, axe y 360 px |
| `tls-handshake` | Perfil TLS autofirmado y handshakes |

Artefactos: cobertura XML/HTML, reporte Playwright, JSON de axe, reporte TLS, `load.json`, `navigation.json`, `memory.json` y logs de smoke.

### 9.2 `nfr-nightly.yml` — schedule y manual

| Job | Contenido |
|---|---|
| `e2e-all-browsers` | Chromium, Firefox y WebKit |
| `perf-local-report` | 100 usuarios/15 min contra el stack local; solo reporte |
| `backup-restore` | Respaldo y simulacro de restauración |
| `storage-report` | Reporte de almacenamiento y crecimiento |

`perf-vps` está en `.github/workflows/perf-vps.yml` y se ejecuta por `workflow_dispatch` con `base_url`; bloquea si `enforce=yes`.

El job de VPS recibe la URL y credenciales por secretos. Si no hay VPS, se omite y el plan lo marca como evidencia pendiente.

## 10. Evidencia y reportes

Todos los reportes generados se guardan en `reports/nfr/` y se suben como artefactos de CI. No se commitean binarios grandes ni resultados con datos personales.

Formato mínimo de un reporte:

```json
{
  "nfr": "RNF-R-2",
  "check_id": "NFR-TC-R-2.1",
  "environment": "vps",
  "commit": "<sha>",
  "timestamp": "<iso-8601>",
  "status": "pass",
  "metrics": {
    "p50_ms": 0,
    "p95_ms": 0,
    "p99_ms": 0,
    "error_rate": 0
  },
  "evidence": "reports/nfr/load.json"
}
```

Evidencia manual:

- RNF-U-3: planilla de tareas, SUS y consentimiento, con códigos de participante.
- RNF-U-1: checklist WCAG manual.
- RNF-C-1: checklist de versiones penúltimas.
- RNF-S-3: informe SSL Labs del dominio de producción.
- RNF-D-1: no hay evidencia; brecha aceptada.

## 11. Exclusiones y brechas

| Elemento | Estado | Motivo |
|---|---|---|
| RNF-D-1 disponibilidad 99,5 % | No verificado | Requiere monitor externo y un mes de datos; decisión del equipo. |
| RNF-U-3 resultados reales | Pendiente | Estudio manual con 3–5 profesores; se entregan protocolo y plantillas. |
| RNF-C-1 Safari/Edge reales y versiones penúltimas | Parcial | Playwright usa motores equivalentes y una versión por motor; checklist manual. |
| RNF-U-2 dispositivos físicos | Parcial | Emulación Playwright; verificación física manual pendiente. |
| RNF-S-3 certificado de producción | Pendiente | Solo certificados autofirmados para pruebas; Certbot/SSL Labs en runbook. |
| RNF-M-2 logs en la nube | Pendiente | Logs JSON locales y auditoría en base; CloudWatch/Loki documentado. |
| RNF-R-3 S3, ciclo de vida y presupuesto | Pendiente | Reporte local y runbook; no hay bucket ni alerta AWS configurada. |
| RNF-D-2 copia fuera del servidor | Pendiente | Respaldo local; S3/offsite documentado. |
| RNF-C-2 magic bytes | Limitación | Solo extensión y MIME declarado; se documenta el riesgo. |
| §2.6 costo, schedule, extensibilidad e interoperabilidad | Fuera de alcance | No son RNF de §4; RF-15 y RF-18 no están implementados. |
| §10 RF-19/RF-21 | Fuera de alcance | Invitaciones/consentimiento y exportación/supresión no implementados. |
| Retención de 12 meses de proyectos | No implementada | El cierre de proyecto no forma parte del alcance actual. |

## 12. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Subir la cobertura de 64 % a 80 % requiere muchos casos de rama | Alto esfuerzo | Priorizar servicios con menor cobertura; escribir pruebas junto con cada cambio. |
| La auditoría toca muchos endpoints | Regresiones | Helper único, pruebas por acción y revisión cruzada. |
| E2E con múltiples motores y base dedicada | Infraestructura frágil | Seed determinista, reset por ejecución y contenedores aislados. |
| Dataset de rendimiento de 33–66 GB | Consumo de disco y tiempo | Archivos dispersos, `tar --sparse` y límites de retención local. |
| Umbrales de rendimiento en CI local | Falsos negativos | Reporte sin bloqueo en CI; bloqueo en VPS. |
| Certificados autofirmados | No representan producción | Pruebas de handshake y runbook de Certbot/SSL Labs. |
| D-1 sin evidencia | No se puede afirmar 99,5 % | Registrar brecha; no declarar cumplimiento. |
| U-3 sin ejecución | No se puede afirmar usabilidad | Ejecutar el estudio antes de E4 o declarar pendiente. |

## 13. Criterios de salida

1. Todos los checks automatizados de L1–L4 pasan en CI, salvo los reportes de rendimiento local que son informativos.
2. La cobertura de lógica de negocio es ≥ 80 %.
3. No hay secretos, contraseñas, tokens ni datos personales en logs o reportes.
4. Cada RNF tiene un estado explícito: verificado automáticamente, verificado manualmente o brecha aceptada.
5. La ejecución en VPS de R-1/R-2 se completa cuando el entorno esté disponible; si no, queda marcada como pendiente.
6. El protocolo U-3 y sus plantillas existen; la ejecución se registra en el Anexo B.
7. `main.tex` no se modifica; `spec/main-tex-nfr-changes.md` contiene todos los cambios propuestos.
8. `README.md` y `GuiaRepo.md` documentan los comandos y archivos nuevos.

## 14. Fases de implementación

| Fase | Entregable |
|---|---|
| 1 | Scaffolding de pruebas, dependencias Playwright/axe, configuración de cobertura y esqueleto de CI. |
| 2 | Bloqueo de login, matriz RBAC, validaciones de subida y de archivos de revisión, y perfil TLS autofirmado. |
| 3 | Auditoría, JSON logs, retención y prueba de esquema sin RUT/calificaciones. |
| 4 | Pruebas de rama para alcanzar 80 % de cobertura. |
| 5 | E2E PA-1/PA-2/PA-5, axe, 360 px y matriz de navegadores. |
| 6 | Seed de rendimiento, generador de carga, reporte de almacenamiento y evidencia VPS. |
| 7 | Respaldo/restauración, runbooks de operación y smoke de Docker. |
| 8 | Reportes finales, actualización de README/GuiaRepo y cierre de brechas. |

## Anexo A. Acciones de auditoría

Ver la tabla de RNF-M-2. Todas las acciones usan entidad y `entidad_id`; el usuario se obtiene de la sesión y la IP del request. La fila se escribe en la misma transacción que la acción cuando esta es de escritura.

## Anexo B. Matriz de roles por endpoint

Todas las rutas, excepto las de `health`, viven bajo el prefijo `/api/v1`. La columna “No participante” se refiere a un usuario autenticado que no participa en el proyecto objetivo; en endpoints de lista, solo se comprueba que no aparezca el proyecto ajeno.

| Método y ruta | Anónimo | No participante | Colaborador | Gestor |
|---|---|---|---|---|
| `POST /auth/login` | Permitido | Permitido | Permitido | Permitido |
| `POST /auth/logout` | 204 (idempotente) | 204 | 204 | 204 |
| `GET /auth/me` | 401 | 200 | 200 | 200 |
| `GET /projects` | 401 | Solo propios; no aparece el ajeno | Solo propios | Solo propios |
| `POST /projects` | 401 | 403 si tipo=estudiante; 201 si tipo=profesor | Igual según tipo global | Igual según tipo global |
| `GET /projects/{id}` | 401 | 404 | 200 | 200 |
| `PATCH /projects/{id}` | 401 | 404 | 403 | 200 |
| `POST /projects/{id}/milestones` | 401 | 404 | 403 | 201 |
| `POST /milestones/{id}/deliverables` | 401 | 404 | 403 | 201 |
| `PATCH /deliverables/{id}` | 401 | 404 | 403 | 200 |
| `GET /deliverables/{id}` | 401 | 404 | 200 | 200 |
| `GET /deliverables/{id}/submissions` | 401 | 404 | 403 | 200 |
| `POST /deliverables/{id}/submissions` | 401 | 404 | 201 | 403 |
| `POST /deliverables/{id}/reviews` | 401 | 404 | 403 | 201 |
| `POST /deliverables/{id}/messages` | 401 | 404 | 201 | 201 |
| `GET /reviews/pending` | 401 | Lista vacía | Lista vacía | Solo propias |
| `GET /files/{id}/download` | 401 | 404 | 200 solo última | 200 todas |
| `GET /meta` | 200 | 200 | 200 | 200 |
| `GET /health/live` | 200 | 200 | 200 | 200 |
| `GET /health/ready` | 200/503 | 200/503 | 200/503 | 200/503 |

La prueba de inventario OpenAPI debe fallar si aparece una ruta nueva que no esté en esta matriz. Un usuario puede tener roles distintos en proyectos distintos; las pruebas usan cuentas con un rol único en el proyecto objetivo para que la matriz sea inequívoca.

`POST /deliverables/{id}/reviews` usa `multipart/form-data` con `decision` y archivos opcionales. `GET /files/{id}/download` cubre tanto archivos de entrega como archivos adjuntos a una revisión; la regla de “solo última” para colaboradores se aplica a ambos.
