"""Armazenamento dos arquivos bancários originais (imutáveis, endereçados por SHA-256)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


class StorageIntegrityError(Exception):
    pass


class LocalFileStorage:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir.resolve()

    def _path(self, key: str) -> Path:
        path = (self.base_dir / key).resolve()
        if self.base_dir not in path.parents:
            raise ValueError("Chave de armazenamento inválida")
        return path

    @staticmethod
    def key_for(direction: str, sha256: str) -> str:
        return f"{direction.lower()}/{sha256[:2]}/{sha256}.txt"

    def put(self, key: str, content: bytes) -> None:
        path = self._path(key)
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() != hashlib.sha256(content).hexdigest():
                raise StorageIntegrityError(f"Conteúdo divergente já armazenado em {key}")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(content)
        os.replace(tmp, path)

    def get(self, key: str, expected_sha256: str) -> bytes:
        content = self._path(key).read_bytes()
        if hashlib.sha256(content).hexdigest() != expected_sha256:
            raise StorageIntegrityError(f"Hash divergente para {key}")
        return content

    def is_writable(self) -> bool:
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            probe = self.base_dir / ".probe"
            probe.write_bytes(b"ok")
            probe.unlink()
        except OSError:
            return False
        return True
