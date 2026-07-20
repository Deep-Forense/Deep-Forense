"""Seguridad del adaptador de entrada REST: resolución del user_id desde el JWT.

Cierra los TODOs de Sprint 1: /analyze exige un JWT válido (emitido por
auth-service, HS256 con el MISMO JWT_SECRET compartido vía docker-compose) y
GET /jobs/{job_id} lo acepta opcionalmente para decidir detail_level.

El token de auth-service trae `userId` (UUID del usuario) como claim y el
email en `sub`; se usa `userId` como identificador canónico del dueño del job.
"""
import os
from typing import Optional

import jwt
from fastapi import Header, HTTPException

_ALGORITHMS = ["HS256", "HS384", "HS512"]


class JwtUserResolver:
    def __init__(self, secret: str) -> None:
        self._secret = secret

    def resolve(self, authorization: Optional[str]) -> Optional[str]:
        """user_id del Bearer token, o None si no hay token o es inválido."""
        if not authorization or not authorization.startswith("Bearer "):
            return None
        token = authorization[len("Bearer ") :]
        try:
            payload = jwt.decode(token, self._secret, algorithms=_ALGORITHMS)
        except jwt.InvalidTokenError:
            return None
        return payload.get("userId") or payload.get("sub")



_default_resolver = JwtUserResolver(os.getenv("JWT_SECRET", "change-this-secret-in-production"))


def optional_user_id(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    """Dependencia FastAPI: user_id si hay JWT válido, None en caso contrario."""
    return _default_resolver.resolve(authorization)


def require_user_id(authorization: Optional[str] = Header(default=None)) -> str:
    """Dependencia FastAPI: user_id obligatorio; 401 si falta o es inválido."""
    user_id = _default_resolver.resolve(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Se requiere un token JWT válido.")
    return user_id
