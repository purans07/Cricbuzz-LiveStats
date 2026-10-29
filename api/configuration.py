"""Load an operator-reviewed provider manifest and private transport settings."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from api.client import APIError, Endpoint, HTTPPolicy, ProviderContract
from config import PROJECT_ROOT, read_environment


@dataclass(frozen=True)
class APISettings:
    """Credential repr is suppressed to avoid accidental display in diagnostics."""

    contract: ProviderContract
    api_key: str = field(repr=False)
    policy: HTTPPolicy = field(default_factory=HTTPPolicy)


def load_api_settings(environ=None, env_file=None) -> APISettings:
    """Do not choose a subscription or enable a guessed provider endpoint."""
    values = read_environment(environ, env_file)
    raw = values.get("CRICBUZZ_CONTRACT_FILE")
    if not raw:
        raise APIError(
            "configuration",
            "Select a provider/version and configure CRICBUZZ_CONTRACT_FILE first.",
        )
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    try:
        if path.stat().st_size > 100_000:
            raise ValueError
        payload = json.loads(path.read_text())
        if payload.get("verified") is not True:
            raise ValueError
        endpoints = {}
        for name, record in payload["endpoints"].items():
            endpoints[name] = Endpoint(
                path=record["path"],
                required_query=tuple(record.get("required_query", [])),
                optional_query=tuple(record.get("optional_query", [])),
                cursor_param=record.get("cursor_param"),
                items_path=tuple(record.get("items_path", [])),
                next_cursor_path=tuple(record.get("next_cursor_path", [])),
            )
        contract = ProviderContract(
            payload["provider"],
            payload["version"],
            payload["base_url"],
            payload["auth_header"],
            endpoints,
            True,
            payload.get("static_headers", {}),
        )
        contract.validate()
        policy = HTTPPolicy(**payload.get("http_policy", {}))
        policy.validate()
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise APIError(
            "configuration", "Provider manifest is absent, invalid or unverified."
        ) from None
    credential = values.get("CRICBUZZ_API_KEY", "")
    if (
        not isinstance(credential, str)
        or not credential.strip()
        or any(c in credential for c in "\r\n")
    ):
        raise APIError(
            "configuration",
            "Configure CRICBUZZ_API_KEY privately after selecting provider access.",
        )
    return APISettings(contract, credential, policy)
