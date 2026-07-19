import httpx

from app.infrastructure.adapter.output import http_retry


async def test_transient_429_is_retried(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429 if len(calls) == 1 else 200, request=request)

    async def no_sleep(_delay):
        return None

    monkeypatch.setattr(http_retry.asyncio, "sleep", no_sleep)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    response = await http_retry.post_with_retry(client, "https://provider.test/api")

    assert response.status_code == 200
    assert len(calls) == 2


async def test_non_transient_400_is_not_retried():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(400, request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    response = await http_retry.post_with_retry(client, "https://provider.test/api")

    assert response.status_code == 400
    assert len(calls) == 1
