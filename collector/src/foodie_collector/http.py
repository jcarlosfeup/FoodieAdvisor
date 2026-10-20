"""HTTP helpers shared by the open-data sources: retries with exponential backoff."""

import logging
import time
from collections.abc import Callable

import httpx

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def build_client(user_agent: str, timeout_seconds: float, **kwargs) -> httpx.Client:
    return httpx.Client(headers={"User-Agent": user_agent}, timeout=timeout_seconds, **kwargs)


def _retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def request_with_retries(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    max_attempts: int,
    backoff_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
    **kwargs,
) -> httpx.Response:
    """Send a request, retrying transport errors and 429/5xx responses.

    Waits backoff_seconds * 2**(attempt - 1) between attempts, or the server's Retry-After
    when present. Other 4xx responses raise immediately.
    """
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        delay = backoff_seconds * 2 ** (attempt - 1)
        try:
            response = client.request(method, url, **kwargs)
        except httpx.TransportError as error:
            last_error = error
        else:
            if response.status_code not in RETRYABLE_STATUS_CODES:
                response.raise_for_status()
                return response
            last_error = httpx.HTTPStatusError(
                f"HTTP {response.status_code} from {url}", request=response.request, response=response
            )
            delay = _retry_after_seconds(response) or delay
        if attempt < max_attempts:
            logger.warning(
                "request failed, retrying",
                extra={"url": url, "attempt": attempt, "delay_seconds": delay, "error": str(last_error)},
            )
            sleep(delay)
    assert last_error is not None
    raise last_error
