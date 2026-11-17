# Respaldos y simulacro de restauración

## Objetivo

Cumplir RNF-D-2: RPO de 24 horas y RTO de 4 horas para PostgreSQL y los archivos subidos.

## Requisitos

- Stack `db` y `backend` levantado.
- `python3`, `sha256sum`, `tar` y Docker disponibles en el host.
- Suficiente espacio local para el dump y el archivo de subidas.

## Crear un respaldo

```bash
./scripts/nfr/backup.sh
```

El script crea en `backups/`:

- `db-<timestamp>.dump`: `pg_dump -Fc` de PostgreSQL;
- `uploads-<timestamp>.tar.gz`: `tar --sparse` de `/app/uploads`;
- `manifest-<timestamp>.json`: hashes SHA-256, tamaños, conteos de tablas y cantidad de archivos.

La retención local es de 30 días y se controla con `RETENTION_DAYS`:

```bash
RETENTION_DAYS=14 ./scripts/nfr/backup.sh
```

`backups/` está ignorado por Git porque contiene datos personales y académicos.

## Simulacro de restauración

```bash
./scripts/nfr/restore_drill.sh
```

El simulacro:

1. toma el manifiesto más reciente;
2. verifica los SHA-256 del dump y del archivo de subidas;
3. calcula la antigüedad del respaldo y comprueba el RPO de 24 horas;
4. inicia un contenedor PostgreSQL desechable;
5. restaura el dump con `pg_restore`;
6. compara los conteos de las tablas principales;
7. extrae las subidas en un directorio temporal y compara la cantidad de archivos;
8. mide el tiempo de restauración y comprueba el RTO de 4 horas;
9. escribe `reports/nfr/restore-drill.json`.

Se pueden ajustar los objetivos:

```bash
RPO_HOURS=24 RTO_HOURS=4 ./scripts/nfr/restore_drill.sh
```

El contenedor y el directorio temporal se eliminan al terminar. La base de datos y las subidas reales no se tocan.

## Programación

En producción, ejecutar el respaldo a diario con cron o un timer de systemd. Ejemplo de cron:

```cron
0 2 * * * cd /ruta/al/proyecto && ./scripts/nfr/backup.sh >> backups/backup.log 2>&1
```

El workflow `.github/workflows/nfr-nightly.yml` ejecuta respaldo, simulacro y reporte de almacenamiento en modo nightly/manual.

## Producción (pendiente)

- Copiar los respaldos fuera del servidor (S3 u otro almacenamiento cifrado).
- Cifrar los respaldos en reposo.
- Conservar 30 días los respaldos y 12 meses la auditoría según §5.3.
- Alertar si el respaldo diario falla o si el simulacro supera el RTO.
- Documentar la restauración en el VPS y medir un RTO real.

## Limitaciones

- El respaldo actual es local; no protege contra la pérdida total del servidor.
- El simulacro usa un PostgreSQL desechable en el mismo host; no mide la recuperación de un VPS completo.
- El manifest no incluye el contenido de los archivos; la integridad se verifica con el SHA-256 del archivo comprimido y el conteo restaurado.
