from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Error de aplicación con código estable y mensaje para el usuario."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


async def app_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Devuelve el formato uniforme de errores de la API."""
    if not isinstance(exc, AppError):
        raise exc

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )
