from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol

import aiofiles

from app.core.config import settings


class StorageBackend(Protocol):
    """Contrato mínimo para persistir archivos."""

    async def save(self, key: str, chunks: AsyncIterator[bytes]) -> None: ...

    async def delete(self, key: str) -> None: ...

    def path(self, key: str) -> Path: ...

    async def exists(self, key: str) -> bool: ...


class LocalStorage:
    """Almacenamiento local privado bajo un directorio raíz."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _resolve(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if path != self.root and self.root not in path.parents:
            raise ValueError("Storage key escapes the configured root.")
        return path

    async def save(self, key: str, chunks: AsyncIterator[bytes]) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with aiofiles.open(path, "wb") as handle:
                async for chunk in chunks:
                    await handle.write(chunk)
        except Exception:
            path.unlink(missing_ok=True)
            raise

    async def delete(self, key: str) -> None:
        self._resolve(key).unlink(missing_ok=True)

    def path(self, key: str) -> Path:
        return self._resolve(key)

    async def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()


_storage: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """Devuelve el backend de almacenamiento configurado."""
    global _storage

    if _storage is None:
        _storage = LocalStorage(Path(settings.upload_dir))
    return _storage
