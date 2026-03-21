"""Temporal client singleton."""

from django.conf import settings
from temporalio.client import Client

_client: Client | None = None


def _is_temporal_cloud() -> bool:
    return bool(getattr(settings, "TEMPORAL_API_KEY", ""))


async def get_temporal_client() -> Client:
    global _client
    if _client is None:
        host = f"{settings.TEMPORAL_HOST}:{settings.TEMPORAL_PORT}"
        if _is_temporal_cloud():
            _client = await Client.connect(
                host,
                namespace=settings.TEMPORAL_NAMESPACE,
                api_key=settings.TEMPORAL_API_KEY,
                tls=True,
            )
        else:
            _client = await Client.connect(host)
    return _client
