from __future__ import annotations

import logging
import os
import time
import threading

import msal
from azure.core.credentials import AccessToken, TokenCredential
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

logger = logging.getLogger(__name__)

COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"

# Azure CLI's registered application id
_AZ_CLI_CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"

_credential = None
_token_provider = None


class _AzCliCacheCredential(TokenCredential):
    """Credential that reads the mounted az-CLI MSAL token cache.

    Inside dev containers the SDK's SharedTokenCacheCredential cannot
    find the az-CLI cache because it lives at ``~/.azure/msal_token_cache.json``
    while the SDK looks at ``~/.IdentityService/msal.cache``.

    This class bridges the gap by using MSAL directly.
    """

    def __init__(self, cache_path: str, authority: str):
        self._cache_path = cache_path
        self._authority = authority
        self._lock = threading.Lock()

    def get_token(self, *scopes, **_kwargs) -> AccessToken:
        with self._lock:
            cache = msal.SerializableTokenCache()
            with open(self._cache_path) as f:
                cache.deserialize(f.read())
            app = msal.PublicClientApplication(
                _AZ_CLI_CLIENT_ID,
                authority=self._authority,
                token_cache=cache,
            )
            accounts = app.get_accounts()
            if not accounts:
                raise Exception("No accounts in az-CLI MSAL cache")
            result = app.acquire_token_silent(list(scopes), account=accounts[0])
            if not result or "access_token" not in result:
                # Try force refresh
                result = app.acquire_token_silent(
                    list(scopes), account=accounts[0], force_refresh=True
                )
            if result and "access_token" in result:
                return AccessToken(
                    result["access_token"],
                    int(result.get("expires_in", 3600)) + int(time.time()),
                )
            error = result.get("error_description", "unknown") if result else "no result"
            raise Exception(f"MSAL acquire_token_silent failed: {error}")


def _try_cli_cache_credential():
    """Build a credential backed by the az CLI MSAL cache (dev-container)."""
    cache_path = os.path.join(os.path.expanduser("~"), ".azure", "msal_token_cache.json")
    if not os.path.exists(cache_path):
        return None
    authority = "https://login.microsoftonline.com/e6e6c3b7-14a4-4b8a-940e-37cf5d6507c7"
    return _AzCliCacheCredential(cache_path, authority)


def get_credential():
    global _credential
    if _credential is None:
        # 1. Try the mounted az-CLI token cache (dev-container path)
        cred = _try_cli_cache_credential()
        if cred is not None:
            try:
                cred.get_token(COGNITIVE_SCOPE)
                logger.info("Authenticated via az-CLI MSAL cache")
                _credential = cred
                return _credential
            except Exception:
                logger.debug("az-CLI cache credential failed", exc_info=True)
        # 2. Fall back to the full DefaultAzureCredential chain
        _credential = DefaultAzureCredential()
    return _credential


def get_openai_token_provider():
    global _token_provider
    if _token_provider is None:
        _token_provider = get_bearer_token_provider(get_credential(), COGNITIVE_SCOPE)
    return _token_provider
