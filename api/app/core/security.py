"""Write-endpoint authentication: a single shared API key (ADR-011).

There are no users, no sessions and no JWT: TerraPlan and the simulator authenticate with
`X-API-Key`, and every read endpoint stays public.
"""

import hmac
from typing import Annotated

from fastapi import Header

from app.core.config import get_settings
from app.core.errors import UnauthorizedError


def get_ingest_key(x_api_key: Annotated[str | None, Header()] = None) -> str:
    """Validate `X-API-Key` in constant time.

    Comparison is `hmac.compare_digest` so a wrong key leaks no timing information, and the
    received value is never logged nor echoed back in the problem document.
    """
    expected = get_settings().ingest_api_key
    if x_api_key is None or not hmac.compare_digest(
        x_api_key.encode("utf-8"), expected.encode("utf-8")
    ):
        raise UnauthorizedError("Falta la API key o no es válida.")
    return x_api_key
