# TLS local y de producción

## Objetivo

Verificar que la aplicación solo acepta TLS 1.2 o superior, que las cookies de sesión viajan con `Secure` y que el tráfico HTTP se redirige a HTTPS (RNF-S-3).

## Prueba local

```bash
./scripts/nfr/tls_smoke.sh
```

El script:

1. genera certificados autofirmados en `certs/` (ignorado por Git);
2. levanta `db`, `backend` y `web` con `compose.tls.yaml`;
3. espera `https://localhost:8443/health/ready`;
4. ejecuta el seed;
5. ejecuta `scripts/nfr/tls_check.py`.

El perfil TLS no expone el backend en el host. La web queda en:

- HTTP: `http://localhost:8081` (redirige a `https://localhost:8443`)
- HTTPS: `https://localhost:8443`

Para eliminar el stack al terminar:

```bash
TLS_CLEANUP=1 ./scripts/nfr/tls_smoke.sh
```

El certificado autofirmado sirve solo para pruebas. No debe usarse en producción.

## Qué verifica `tls_check.py`

- handshake TLS 1.2 correcto;
- handshake TLS 1.3 correcto;
- TLS 1.0 y 1.1 rechazados;
- `/health/ready` responde por HTTPS;
- cabecera `Strict-Transport-Security`;
- redirección HTTP → HTTPS;
- cookie `hito_session` con atributo `Secure` cuando se proporciona `DEMO_PASSWORD`;
- configuración estática de Nginx y `compose.tls.yaml`.

## Producción (demo)

El demo público usa un proxy Nginx/Certbot en contenedores, sin `sudo` en el host:

1. El dominio apunta al host.
2. El router reenvía TCP `80` y TCP `443` al host. El `80` se usa para el desafío ACME y la redirección; el `443` para HTTPS.
3. `scripts/cd/setup-nginx-tls.sh` levanta `compose.proxy.yaml`, solicita o reutiliza el certificado en `proxy/certbot/conf`, renderiza `deploy/nginx/https.conf.template`, verifica `https://<dominio>/health/ready` de forma local y redirige HTTP a HTTPS.
4. El proxy comparte la red Docker `hito_default` con el demo y usa `proxy_pass http://web:80`. El contenedor web queda en `127.0.0.1:9080`.
5. `.env.demo` activa `SESSION_COOKIE_SECURE=true` y `TRUST_PROXY_HEADERS=true`.
6. La renovación se ejecuta con:
   ```bash
   ./scripts/cd/renew-certificates.sh
   ```
   Para probar el flujo sin cambiar el certificado:
   ```bash
   ./scripts/cd/renew-certificates.sh --dry-run
   ```
   Programa una ejecución diaria con `crontab -e` en el servidor:
   ```cron
   17 3 * * * cd /home/fgonzalez/hito && ./scripts/cd/renew-certificates.sh >> renew.log 2>&1
   ```
7. La auditoría SSL Labs queda pendiente.

El certificado vive en `proxy/certbot/conf`, que es propiedad de root. Por eso los scripts lo comprueban dentro de un contenedor y no desde el usuario del host.

Si `https://<dominio>` muestra un certificado que no corresponde al dominio, el puerto `443` no está llegando al host. Revisa el port forwarding o desactiva la administración remota del router en ese puerto.

## Limitaciones

- El certificado autofirmado del perfil local no valida la cadena de confianza ni el dominio.
- El perfil local usa los puertos `8081`/`8443` para no chocar con el stack HTTP de desarrollo.
- La auditoría SSL Labs de producción queda pendiente.
