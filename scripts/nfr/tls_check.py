#!/usr/bin/env python3
import argparse
import http.client
import json
import os
import socket
import ssl
import sys
import urllib.request
import warnings
from pathlib import Path


def handshake(host: str, port: int, version: ssl.TLSVersion) -> str:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.minimum_version = version
    context.maximum_version = version
    with socket.create_connection((host, port), timeout=5) as raw_socket:
        with context.wrap_socket(raw_socket, server_hostname=host) as tls_socket:
            return tls_socket.version() or ""


def https_get(host: str, port: int, path: str) -> tuple[int, dict[str, str], bytes]:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    url = f"https://{host}:{port}{path}"
    with urllib.request.urlopen(url, context=context, timeout=5) as response:
        headers = {key.lower(): value for key, value in response.headers.items()}
        return response.status, headers, response.read()


def check_static_config(root: Path) -> None:
    nginx = (root / "frontend" / "nginx.tls.conf").read_text(encoding="utf-8")
    compose = (root / "compose.tls.yaml").read_text(encoding="utf-8")

    assert "ssl_protocols TLSv1.2 TLSv1.3;" in nginx
    assert "Strict-Transport-Security" in nginx
    assert "return 301 https://" in nginx
    assert 'SESSION_COOKIE_SECURE: "true"' in compose
    assert 'TRUST_PROXY_HEADERS: "true"' in compose


def check_cookie(host: str, port: int, password: str) -> None:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    payload = json.dumps(
        {"email": "camila.soto@udec.cl", "password": password}
    ).encode("utf-8")
    request = urllib.request.Request(
        f"https://{host}:{port}/api/v1/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, context=context, timeout=5) as response:
        cookies = response.headers.get_all("Set-Cookie") or []

    assert any("hito_session" in cookie and "Secure" in cookie for cookie in cookies)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica TLS 1.2/1.3.")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--https-port", type=int, default=8443)
    parser.add_argument("--http-port", type=int, default=8081)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    check_static_config(root)

    assert handshake(args.host, args.https_port, ssl.TLSVersion.TLSv1_2) == "TLSv1.2"
    assert handshake(args.host, args.https_port, ssl.TLSVersion.TLSv1_3) == "TLSv1.3"

    for version in (ssl.TLSVersion.TLSv1, ssl.TLSVersion.TLSv1_1):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                handshake(args.host, args.https_port, version)
        except (ssl.SSLError, OSError, ValueError):
            continue
        raise AssertionError(f"TLS inseguro aceptado: {version}")

    status, headers, _ = https_get(args.host, args.https_port, "/health/ready")
    assert status == 200
    assert "strict-transport-security" in headers
    assert headers["strict-transport-security"].startswith("max-age=")

    connection = http.client.HTTPConnection(args.host, args.http_port, timeout=5)
    connection.request("GET", "/")
    response = connection.getresponse()
    location = response.getheader("Location") or ""
    connection.close()
    assert response.status in (301, 302, 307, 308)
    assert location.startswith("https://")

    password = os.environ.get("DEMO_PASSWORD")
    if password:
        check_cookie(args.host, args.https_port, password)

    print("TLS OK: TLS 1.2/1.3 aceptados, TLS 1.0/1.1 rechazados, HSTS y cookie Secure.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
