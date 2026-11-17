from fastapi import Request

from app.core.config import settings


def get_client_ip(request: Request) -> str:
    """Obtiene la IP del cliente, respetando proxies de confianza."""
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-real-ip")
        if not forwarded:
            forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

    if request.client is None:
        return "unknown"
    return request.client.host
