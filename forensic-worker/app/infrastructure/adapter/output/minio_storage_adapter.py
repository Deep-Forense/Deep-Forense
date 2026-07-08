"""Adaptador de salida: MinioStorageAdapter (vista del worker).

Lee artifacts subidos por forensic-api (storage_ref = '{bucket}/{path}') y
guarda derivados del pipeline (ela_heatmap.png) en el bucket configurado.
"""
import asyncio
import io

from minio import Minio

from app.domain.ports.storage_port import StoragePort


class MinioStorageAdapter(StoragePort):
    def __init__(self, client: Minio, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def get(self, storage_ref: str) -> bytes:
        return await asyncio.to_thread(self._get_sync, storage_ref)

    def _get_sync(self, storage_ref: str) -> bytes:
        bucket, _, path = storage_ref.partition("/")
        if not path:
            raise ValueError(f"storage_ref inválido (se espera 'bucket/path'): {storage_ref!r}")
        response = self._client.get_object(bucket, path)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def save(self, path: str, content: bytes) -> str:
        await asyncio.to_thread(self._save_sync, path, content)
        return f"{self._bucket}/{path}"

    def _save_sync(self, path: str, content: bytes) -> None:
        self._client.put_object(
            bucket_name=self._bucket,
            object_name=path,
            data=io.BytesIO(content),
            length=len(content),
        )
