"""OpenAI-compatible request forwarding to upstream backends."""

import logging
from typing import Any

import httpx

from inference_gateway.core.config import GatewayConfig
from inference_gateway.core.exceptions import UpstreamTimeoutError, UpstreamUnreachableError

logger = logging.getLogger(__name__)


async def forward_chat_completion(
    request_body: dict[str, Any],
    base_url: str,
    config: GatewayConfig,
) -> httpx.Response:
    """
    Forward a chat completion request to upstream backend.

    Args:
        request_body: The request body dict to forward
        base_url: Base URL of the upstream backend
        config: Gateway configuration for timeout settings

    Returns:
        httpx.Response object from upstream

    Raises:
        UpstreamUnreachableError: If connection to upstream fails
        UpstreamTimeoutError: If upstream request times out
    """
    url = f"{base_url.rstrip('/')}/v1/chat/completions"

    timeout = httpx.Timeout(
        config.timeout_s,
        connect=config.connect_timeout_s,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.debug(f"Forwarding chat completion to {url}")
            response = await client.post(
                url,
                json=request_body,
                headers={"Content-Type": "application/json"},
            )
            return response

    except (httpx.ConnectError, httpx.NetworkError) as e:
        logger.error(f"Connection error to upstream {url}: {e}")
        raise UpstreamUnreachableError(
            f"Connection to upstream failed: {str(e)}",
            upstream=base_url,
        ) from e

    except httpx.TimeoutException as e:
        logger.error(f"Timeout error to upstream {url}: {e}")
        raise UpstreamTimeoutError(
            "Inference backend did not respond in time",
            upstream=base_url,
        ) from e


async def forward_models(
    base_url: str,
    config: GatewayConfig,
) -> httpx.Response:
    """
    Forward a models list request to upstream backend.

    Args:
        base_url: Base URL of the upstream backend
        config: Gateway configuration for timeout settings

    Returns:
        httpx.Response object from upstream

    Raises:
        UpstreamUnreachableError: If connection to upstream fails
        UpstreamTimeoutError: If upstream request times out
    """
    url = f"{base_url.rstrip('/')}/v1/models"

    timeout = httpx.Timeout(
        config.timeout_s,
        connect=config.connect_timeout_s,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.debug(f"Forwarding models request to {url}")
            response = await client.get(url)
            return response

    except (httpx.ConnectError, httpx.NetworkError) as e:
        logger.error(f"Connection error to upstream {url}: {e}")
        raise UpstreamUnreachableError(
            f"Connection to upstream failed: {str(e)}",
            upstream=base_url,
        ) from e

    except httpx.TimeoutException as e:
        logger.error(f"Timeout error to upstream {url}: {e}")
        raise UpstreamTimeoutError(
            "Inference backend did not respond in time",
            upstream=base_url,
        ) from e
