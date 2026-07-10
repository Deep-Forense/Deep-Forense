"""Tests del cierre de Sprint 1 — resolución de user_id desde el JWT.

Los tokens se firman localmente con pyjwt (mismo formato HS256 que emite
auth-service: sub=email, claim userId).
"""
from datetime import datetime, timedelta, timezone

import jwt

from app.infrastructure.adapter.input.rest.security import JwtUserResolver

SECRET = "secreto-de-test-suficientemente-largo-para-hs256"
resolver = JwtUserResolver(SECRET)


def _token(secret=SECRET, expired=False, **claims):
    payload = {
        "sub": "user@example.com",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=-5 if expired else 5),
        **claims,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_resolves_user_id_claim():
    token = _token(userId="uuid-123")
    assert resolver.resolve(f"Bearer {token}") == "uuid-123"


def test_falls_back_to_sub_when_no_user_id_claim():
    token = _token()
    assert resolver.resolve(f"Bearer {token}") == "user@example.com"


def test_missing_header_returns_none():
    assert resolver.resolve(None) is None
    assert resolver.resolve("") is None


def test_non_bearer_header_returns_none():
    assert resolver.resolve("Basic abc123") is None


def test_wrong_signature_returns_none():
    token = _token(secret="otro-secreto-distinto-tambien-largo!!")
    assert resolver.resolve(f"Bearer {token}") is None


def test_expired_token_returns_none():
    token = _token(expired=True, userId="uuid-123")
    assert resolver.resolve(f"Bearer {token}") is None
