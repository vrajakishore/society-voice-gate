from __future__ import annotations

from azure.identity import DefaultAzureCredential, get_bearer_token_provider

COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"

_credential: DefaultAzureCredential | None = None
_token_provider = None


def get_credential() -> DefaultAzureCredential:
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


def get_openai_token_provider():
    global _token_provider
    if _token_provider is None:
        _token_provider = get_bearer_token_provider(get_credential(), COGNITIVE_SCOPE)
    return _token_provider
