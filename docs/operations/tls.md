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

## Producción (pendiente)

El repositorio no incluye un dominio ni un certificado de producción. Para desplegar:

1. Apuntar el dominio al VPS.
2. Instalar Certbot y emitir el certificado:
   ```bash
   sudo certbot certonly --webroot -w /var/www/certbot -d <dominio>
   ```
3. Montar `/etc/letsencrypt/live/<dominio>/fullchain.pem` y `privkey.pem` en el contenedor web.
4. Mantener `ssl_protocols TLSv1.2 TLSv1.3`, HSTS y la redirección HTTP → HTTPS.
5. Configurar `SESSION_COOKIE_SECURE=true` y `TRUST_PROXY_HEADERS=true`.
6. Renovar con el timer de Certbot y recargar Nginx.
7. Ejecutar SSL Labs sobre el dominio y guardar el informe como evidencia.

## Limitaciones

- El certificado autofirmado no valida la cadena de confianza ni el dominio.
- La auditoría SSL Labs de producción queda pendiente hasta contar con el VPS y el dominio.
- El perfil local usa los puertos `8081`/`8443` para no chocar con el stack HTTP de desarrollo.
