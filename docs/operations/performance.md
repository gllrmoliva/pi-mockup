# Rendimiento y dimensionamiento AWS

## Objetivo

Verificar RNF-R-1 (p95 ≤ 500 ms en navegación y ≤ 3 s en subida) y RNF-R-2 (100 usuarios concurrentes durante 15 minutos, p95 de R-1 y tasa de error < 1 %), y registrar el consumo de RAM para estimar el tamaño de instancia AWS.

## Stack de rendimiento

```bash
PERF_CLEANUP=1 ./scripts/nfr/perf.sh
```

El script usa el proyecto Compose `hito_perf`:

- base `hito_perf`;
- web en `http://localhost:18081`;
- backend no expuesto al host;
- dataset SRS completo: 675 cuentas, 529 proyectos, 2.645 hitos, 5.290 entregables, 13.225 entregas y 6.615 archivos dispersos de 5–10 MB.

Para una verificación rápida sin esperar 15 minutos:

```bash
PERF_USERS=10 PERF_DURATION=30 PERF_RAMP_UP=5 PERF_CLEANUP=1 ./scripts/nfr/perf.sh
```

El seed completo se ejecuta una vez; el smoke sigue usando el dataset completo.

## Qué se ejecuta

1. `app.seed_perf` siembra el dataset y crea archivos dispersos.
2. `scripts/nfr/load_test.py` corre dentro del contenedor `backend-test` contra `http://web`.
3. `frontend/e2e/perf.spec.ts` mide navegación y una subida de 10 MB con Playwright.
4. `scripts/nfr/memory_sampler.py` muestrea `docker stats` cada 5 segundos.
5. `scripts/nfr/memory_report.py` resume el pico y la media de RAM.

Mezcla de carga:

| Acción | Porcentaje |
|---|---:|
| Listar proyectos | 35 % |
| Detalle de proyecto | 20 % |
| Detalle de entregable | 15 % |
| Bandeja de revisión | 10 % |
| Descarga de archivo | 15 % |
| Escrituras (mensaje, entrega, revisión) | 5 % |

Las revisiones de carga se envían como `form data` con `decision` y sin archivos; el endpoint no usa JSON desde que admite archivos opcionales.

## Reportes

- `reports/nfr/load.json` y `load.md`: p50/p95/p99, errores, throughput y mezcla.
- `reports/nfr/navigation.json`: navegación y subida.
- `reports/nfr/memory.json`: RAM por contenedor, pico, media e instancia sugerida.
- `reports/nfr/memory-samples.jsonl`: muestras crudas de `docker stats`.

`load.json` incluye el bloque `memory` con el resumen de RAM.

## Memoria y costo AWS

El muestreo local usa `docker stats` y excluye el contenedor generador de carga. El pico corresponde a `backend`, `db` y `web`.

Regla de dimensionamiento:

1. Tomar `peak_total_mib` de `memory.json`.
2. Sumar 30 % para sistema operativo, Nginx, Docker y picos: `recommended_instance_mib`.
3. Elegir la instancia AWS más pequeña con al menos esa memoria.
4. Consultar el precio vigente de AWS Lightsail o EC2 y sumar almacenamiento y correo.
5. Comparar con el límite de USD 10 mensuales de §2.6 y el riesgo R-8.

Ejemplo con el smoke local: pico de 182,47 MiB, instancia sugerida de 256 MiB. Cualquier plan de 512 MB o 1 GB es suficiente para ese perfil; el plan debe confirmarse con una ejecución completa de 100 usuarios. No usar la RAM del host con Docker Desktop como proxy del VPS: incluye overhead de la máquina de desarrollo.

En el VPS, medir además con `free -m`, `docker stats` o CloudWatch. El workflow `perf-vps` no puede inspeccionar contenedores remotos, así que el reporte de memoria de una ejecución VPS debe completarse con esas herramientas.

## Ejecución en VPS

El workflow `.github/workflows/perf-vps.yml` se lanza manualmente con `base_url` y usa el secreto `PERF_PASSWORD`. Con `enforce=yes`, falla si p95 > 500 ms o la tasa de error es ≥ 1 %.

```bash
E2E_BASE_URL=https://tu-dominio \
  PERF_PASSWORD=... \
  python scripts/nfr/load_test.py \
    --base-url https://tu-dominio \
    --users 100 \
    --duration 900 \
    --report reports/nfr/load-vps.json \
    --markdown reports/nfr/load-vps.md \
    --enforce
```

## Limitaciones

- El smoke local con 10 usuarios no demuestra RNF-R-2; la ejecución completa es la evidencia.
- La red local no representa latencia de internet ni un VPS real.
- El pico de RAM local no incluye el sistema operativo del VPS; se aplica el margen del 30 %.
- La medición de subida usa un PDF de 10 MB y la navegación se mide con Playwright en Chromium.
