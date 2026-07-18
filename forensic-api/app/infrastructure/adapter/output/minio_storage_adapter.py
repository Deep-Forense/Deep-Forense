"""Adaptador de salida: MinioStorageAdapter (T1.M2).

Guarda el contenido binario de un artifact en MinIO bajo la ruta
`jobs/{job_id}/...` -- aquí se recibe ya el "path" resuelto por quien
invoca (el use case), así que este adaptador solo sabe hablar con MinIO.
"""
import asyncio
import io

from minio import Minio

from app.domain.ports.storage_port import StoragePort


class MinioStorageAdapter(StoragePort):
    def __init__(self, client: Minio, bucket: str) -> None:
        self._client = client
        self._bucket = bucket
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    async def save(self, path: str, content: bytes) -> str:
        self._client.put_object(
            bucket_name=self._bucket,
            object_name=path,
            data=io.BytesIO(content),
            length=len(content),
        )
        return f"{self._bucket}/{path}"

    async def get(self, storage_ref: str) -> bytes:
        bucket, _, path = storage_ref.partition("/")
        if not path:
            raise ValueError(f"storage_ref inválido (se espera 'bucket/path'): {storage_ref!r}")
        response = self._client.get_object(bucket, path)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
