# Almacenamiento y alerta de crecimiento

## Objetivo

Verificar el RNF-R-3: soportar un crecimiento de 33–66 GB de archivos al año y hasta 100 GB almacenados, sin superar el límite de costo de USD 10 mensuales.

## Reporte local

Con el backend levantado:

```bash
./scripts/nfr/storage_report.sh
```

El comando ejecuta `python -m app.core.storage_report` dentro del contenedor `backend` y escribe `reports/nfr/storage.json`.

El reporte compara:

- **bytes reales:** suma del tamaño aparente de los archivos en `UPLOAD_DIR` (por defecto `/app/uploads`);
- **bytes registrados:** suma de `archivo.tamano` en PostgreSQL.

## Umbrales

| Condición | Estado | Código de salida |
|---|---|---|
| Uso < 80 % y diferencia ≤ 5 % | `ok` | 0 |
| Uso ≥ 80 % o diferencia > 5 % | `warning` | 2 |
| Uso ≥ 100 % | `critical` | 1 |

La cuota por defecto es 100 GB y el umbral de alerta es 80 %. Se pueden cambiar:

```bash
./scripts/nfr/storage_report.sh --quota-gb 100 --alert-percent 80
```

Una diferencia superior a 5 % entre bytes reales y metadatos indica archivos faltantes, huérfanos o metadatos desactualizados.

## Evidencia

El JSON contiene:

- `actual_bytes` y `reported_bytes`;
- `quota_gb` y `alert_percent`;
- `usage_percent`;
- `discrepancy_percent`;
- `status`, `exit_code` y `warnings`.

El archivo se guarda en `reports/`, que está ignorado por Git. En CI o producción debe publicarse como artefacto o enviarse a la herramienta de monitoreo.

## Producción (pendiente)

El repositorio usa un volumen local, no un bucket de objetos. Para producción:

1. Migrar el adaptador de almacenamiento a S3 (o equivalente).
2. Configurar una política de ciclo de vida que elimine archivos 12 meses después del cierre del proyecto.
3. Publicar la métrica de uso de S3 en CloudWatch y una alarma al 80 % de 100 GB.
4. Configurar AWS Budgets con alerta al llegar a USD 8 y límite de USD 10 mensuales.
5. Programar el reporte a diario y conservar el JSON como evidencia.

La retención de 12 meses no está implementada porque el cierre de proyecto está fuera del alcance actual. Sin esa retención, el almacenamiento no se estabiliza en 100 GB; el reporte lo debe tratar como supuesto de dimensionamiento.

## Limitaciones

- El reporte local no demuestra el costo real de nube.
- No reemplaza una alarma de S3/CloudWatch ni una alerta de presupuesto.
- Los archivos dispersos se miden por tamaño aparente (`st_size`), que es el valor relevante para la cuota lógica.
