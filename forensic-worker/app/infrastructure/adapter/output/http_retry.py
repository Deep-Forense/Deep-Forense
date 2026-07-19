"""Reintentos acotados para proveedores HTTP ante fallos transitorios."""
import asyncio
import random

import httpx

_RETRY_STATUSES = {408, 429, 500, 502, 503, 504}


async def post_with_retry(
    client: httpx.AsyncClient, url: str, *, attempts: int = 3, **kwargs
) -> httpx.Response:
    response = None
    for attempt in range(attempts):
        response = await client.post(url, **kwargs)
        if response.status_code not in _RETRY_STATUSES or attempt == attempts - 1:
            return response
        retry_after = response.headers.get("retry-after")
        try:
            delay = min(10.0, float(retry_after)) if retry_after else 2 ** attempt
        except ValueError:
            delay = 2 ** attempt
        await asyncio.sleep(delay + random.uniform(0, 0.25))
    return response
