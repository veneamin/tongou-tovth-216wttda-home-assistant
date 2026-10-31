"""Minimal, self-contained Tuya Cloud API client for Tuya Shower.

The client deliberately avoids importing LocalTuya internals.  It uses the
Home Assistant-managed aiohttp session, signs the exact request-body bytes
that are sent over HTTP, and implements only the Tuya endpoints this
integration needs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

# Tuya data-center endpoints.  These values match the region identifiers
# stored by LocalTuya and used by the Tuya Cloud OpenAPI.
REGION_URLS = {
    "cn": "https://openapi.tuyacn.com",
    "eu": "https://openapi.tuyaeu.com",
    "ea": "https://openapi-ueaz.tuyaus.com",
    "in": "https://openapi.tuyain.com",
    "us": "https://openapi.tuyaus.com",
    "we": "https://openapi-weaz.tuyaeu.com",
    "sg": "https://openapi-sg.iotbing.com",
}

# Tuya returns token validity in seconds.  Refresh slightly early to avoid
# using a token that expires while a request is in flight.
TOKEN_EXPIRY_MARGIN = 30


class TuyaCloudClient:
    """Small async client for the Tuya Cloud API endpoints we use."""

    def __init__(
        self,
        hass,
        region_code: str,
        client_id: str,
        secret: str,
        user_id: str,
    ) -> None:
        """Store credentials and reuse Home Assistant's shared HTTP session."""
        try:
            self._base_url = REGION_URLS[region_code]
        except KeyError as err:
            raise ValueError(f"Unsupported Tuya region: {region_code}") from err

        self._session = async_get_clientsession(hass)
        self._client_id = client_id
        self._secret = secret
        self._user_id = user_id
        self._access_token = ""
        self._token_expire_time = 0

    @property
    def token_validate(self) -> bool:
        """Return True while the cached access token is still valid."""
        return self._token_expire_time - TOKEN_EXPIRY_MARGIN > int(time.time())

    @staticmethod
    def _body_bytes(body: Any | None) -> bytes:
        """Serialize JSON once so hashing and transmission use identical bytes."""
        if body is None:
            return b""
        if isinstance(body, bytes):
            return body
        if isinstance(body, str):
            return body.encode("utf-8")
        return json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )

    def _signature(
        self,
        method: str,
        path: str,
        timestamp: str,
        body: bytes,
        *,
        token_request: bool,
    ) -> str:
        """Build the current Tuya stringToSign and calculate HMAC-SHA256.

        Tuya's current documentation permits an optional nonce.  We omit it
        deliberately to remain compatible with the proven LocalTuya request
        format while still using the current stringToSign/body-hash algorithm.
        """
        content_hash = hashlib.sha256(body).hexdigest()

        # No custom Signature-Headers are used by this integration, so the
        # optional signed-header section is empty and creates a blank line.
        string_to_sign = (
            f"{method.upper()}\n"
            f"{content_hash}\n"
            f"\n"
            f"{path}"
        )

        prefix = self._client_id
        if not token_request:
            prefix += self._access_token
        message = f"{prefix}{timestamp}{string_to_sign}"

        return hmac.new(
            self._secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()

    async def async_make_request(
        self,
        method: str,
        path: str,
        body: Any | None = None,
        *,
        _token_request: bool = False,
        _auth_retry: bool = True,
    ) -> dict[str, Any] | bool:
        """Send one signed Tuya request and return its decoded JSON response."""
        if not _token_request and not self.token_validate:
            token_result = await self.async_get_access_token()
            if token_result != "ok":
                _LOGGER.error("Tuya Cloud token refresh failed: %s", token_result)
                return False

        body_bytes = self._body_bytes(body)
        timestamp = str(int(time.time() * 1000))
        signature = self._signature(
            method,
            path,
            timestamp,
            body_bytes,
            token_request=_token_request,
        )

        headers = {
            "client_id": self._client_id,
            "sign": signature,
            "sign_method": "HMAC-SHA256",
            "t": timestamp,
        }
        if not _token_request:
            headers["access_token"] = self._access_token
        if body is not None:
            headers["Content-Type"] = "application/json"

        try:
            async with self._session.request(
                method.upper(),
                f"{self._base_url}{path}",
                headers=headers,
                data=body_bytes if body is not None else None,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
                if not isinstance(payload, dict):
                    _LOGGER.error("Tuya Cloud returned an unexpected response type")
                    return False

                # Коды 1010–1012 означают, что access token истёк,
                # недействителен или имеет недопустимый статус.
                # Обновляем токен и повторяем исходный запрос только один раз.
                token_error_codes = {"1010", "1011", "1012"}
                error_code = str(payload.get("code", ""))
                if (
                    not _token_request
                    and _auth_retry
                    and not payload.get("success")
                    and error_code in token_error_codes
                ):
                    self._access_token = ""
                    self._token_expire_time = 0
                    token_result = await self.async_get_access_token()
                    if token_result != "ok":
                        _LOGGER.error(
                            "Tuya Cloud token refresh after API error failed: %s",
                            token_result,
                        )
                        return False
                    return await self.async_make_request(
                        method,
                        path,
                        body,
                        _token_request=False,
                        _auth_retry=False,
                    )

                return payload
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            # Never log credentials, signatures, tokens, or complete request
            # headers.  The path contains only fixed API routes and device ID.
            _LOGGER.warning("Tuya Cloud request failed (%s %s): %s", method, path, err)
            return False

    async def async_get_access_token(self) -> str:
        """Request a new simple-mode access token from Tuya Cloud."""
        self._access_token = ""
        self._token_expire_time = 0

        response = await self.async_make_request(
            "GET",
            "/v1.0/token?grant_type=1",
            _token_request=True,
        )
        if not response:
            return "Tuya Cloud did not return a token response"
        if not response.get("success"):
            return (
                f"Tuya token error {response.get('code', 'unknown')}: "
                f"{response.get('msg', 'unknown error')}"
            )

        result = response.get("result") or {}
        access_token = result.get("access_token")
        if not access_token:
            return "Tuya Cloud response did not contain access_token"

        expires_in = int(result.get("expire_time", 3600))
        self._access_token = access_token
        self._token_expire_time = int(time.time()) + expires_in
        return "ok"

    async def async_get_device_query_properties(
        self, device_id: str
    ) -> tuple[dict[str, Any], str]:
        """Read the device's current datapoint properties."""
        response = await self.async_make_request(
            "GET",
            f"/v2.0/cloud/thing/{device_id}/shadow/properties",
        )
        if not response:
            return {}, "Tuya Cloud request failed"
        if not response.get("success"):
            return {}, (
                f"Tuya error {response.get('code', 'unknown')}: "
                f"{response.get('msg', 'unknown error')}"
            )
        result = response.get("result")
        if not isinstance(result, dict):
            return {}, "Tuya Cloud returned an invalid properties payload"
        return result, "ok"

    async def async_connect(self) -> tuple[bool, str]:
        """Check that credentials can obtain a valid cloud token."""
        result = await self.async_get_access_token()
        return (True, "ok") if result == "ok" else (False, result)
