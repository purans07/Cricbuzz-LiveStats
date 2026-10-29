"""Provider-neutral GET transport; endpoint contracts are supplied explicitly."""

import json
import logging
import math
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from string import Formatter
from urllib.parse import quote, urlsplit

import requests

LOG = logging.getLogger(__name__)


class APIError(RuntimeError):
    """Safe application error with no response body, URL, headers or credentials."""

    def __init__(self, code: str, message: str, retry_after: float | None = None):
        """Retain validated dependencies for this component without performing its operations."""
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


@dataclass(frozen=True)
class Endpoint:
    """One verified operation and optional explicit cursor-pagination contract."""

    path: str
    required_query: tuple[str, ...] = ()
    optional_query: tuple[str, ...] = ()
    cursor_param: str | None = None
    items_path: tuple[str, ...] = ()
    next_cursor_path: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderContract:
    """Do not instantiate for production until provider documentation is checked."""

    provider: str
    version: str
    base_url: str
    auth_header: str
    endpoints: dict[str, Endpoint]
    verified: bool = False
    static_headers: dict[str, str] = field(default_factory=dict)

    def validate(self):
        """Limit credentials to a fixed HTTPS origin and declared safe paths."""
        try:
            parsed = urlsplit(self.base_url)
            port = parsed.port
        except (ValueError, TypeError, AttributeError):
            raise APIError("configuration", "Invalid provider base URL.") from None
        if (
            not self.verified
            or not self.provider
            or not self.version
            or parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or port not in {None, 443}
        ):
            raise APIError(
                "configuration", "A verified HTTPS provider contract is required."
            )
        header_name = re.compile(r"[A-Za-z0-9-]+")
        if not header_name.fullmatch(self.auth_header):
            raise APIError("configuration", "Invalid credential header name.")
        if self.auth_header.lower() in {"host", "content-length", "cookie"}:
            raise APIError("configuration", "Unsupported credential header.")
        for key, value in self.static_headers.items():
            if (
                not header_name.fullmatch(key)
                or key.lower() == self.auth_header.lower()
                or key.lower() in {"host", "content-length", "cookie", "authorization"}
                or key.lower().endswith(("-key", "-token"))
                or not isinstance(value, str)
                or "\n" in value
                or "\r" in value
            ):
                raise APIError("configuration", "Invalid static request headers.")
        for operation, endpoint in self.endpoints.items():
            if not re.fullmatch(r"[a-z][a-z0-9_]*", operation):
                raise APIError("configuration", "Invalid operation name.")
            path = endpoint.path
            if (
                not path.startswith("/")
                or path.startswith("//")
                or any(char in path for char in ("?", "#", "\\", "%"))
                or ".." in path
                or "://" in path
            ):
                raise APIError(
                    "configuration", "Endpoint must be a fixed relative path."
                )
            try:
                parts = list(Formatter().parse(path))
                if any(spec or conversion for _, _, spec, conversion in parts):
                    raise ValueError
                fields = [name for _, name, _, _ in parts if name is not None]
            except ValueError:
                raise APIError(
                    "configuration", "Invalid endpoint path template."
                ) from None
            if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) for name in fields):
                raise APIError("configuration", "Invalid path parameter name.")
            if endpoint.cursor_param and not endpoint.next_cursor_path:
                raise APIError(
                    "configuration", "Pagination needs an explicit continuation path."
                )


@dataclass(frozen=True)
class HTTPPolicy:
    """Local protective limits, not claims about a provider's actual quota."""

    connect_timeout: float = 3
    read_timeout: float = 5
    max_attempts: int = 3
    retry_delay: float = 0.25
    max_retry_wait: float = 2
    operation_budget: float = 20
    max_bytes: int = 2_000_000
    min_interval: float = 1

    def validate(self):
        """Reject unsupported configuration values before any request or database operation."""
        for name in (
            "connect_timeout",
            "read_timeout",
            "retry_delay",
            "max_retry_wait",
            "operation_budget",
            "min_interval",
        ):
            value = getattr(self, name)
            if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
                raise APIError(
                    "configuration", "HTTP limits must be finite non-negative numbers."
                )
        if min(self.connect_timeout, self.read_timeout, self.operation_budget) <= 0:
            raise APIError("configuration", "Timeouts must be positive.")
        if (
            type(self.max_attempts) is not int
            or not 1 <= self.max_attempts <= 5
            or type(self.max_bytes) is not int
            or not 1 <= self.max_bytes <= 10_000_000
        ):
            raise APIError(
                "configuration", "HTTP attempts or response size is out of bounds."
            )


@dataclass(frozen=True)
class APIResponse:
    """Validated JSON and safe provenance; no original requests.Response retained."""

    data: dict | list
    provider: str
    version: str
    operation: str
    fetched_at: str
    is_mock: bool
    quota: dict[str, str]


def _path(data, keys):
    """Resolve a reviewed JSON key path without evaluating user-supplied expressions."""
    try:
        for key in keys:
            data = data[key]
        return data
    except (KeyError, TypeError, IndexError):
        raise APIError(
            "shape", "Response does not match the configured pagination contract."
        ) from None


class CricbuzzClient:
    """Perform credentialed requests only against a reviewed provider contract."""

    def __init__(
        self,
        contract: ProviderContract,
        api_key: str,
        *,
        policy=None,
        session=None,
        sleep=time.sleep,
        clock=time.monotonic,
    ):
        """Retain validated dependencies for this component without performing its operations."""
        contract.validate()
        if (
            not isinstance(api_key, str)
            or not api_key.strip()
            or any(c in api_key for c in "\r\n")
        ):
            raise APIError("configuration", "A private API credential is required.")
        self.contract = contract
        self.policy = policy or HTTPPolicy()
        self.policy.validate()
        self._key = api_key
        self._session = session or requests.Session()
        self._session.trust_env = False
        self._sleep, self._clock = sleep, clock
        self._next_allowed = 0.0

    def close(self):
        """Release the HTTP session and clear the retained credential reference."""
        try:
            self._session.close()
        finally:
            self._key = ""

    def _request_parts(self, operation, path_params, query):
        """Build a request only from the reviewed endpoint and validated parameters."""
        if operation not in self.contract.endpoints:
            raise APIError(
                "configuration", "Operation is not in the verified contract."
            )
        endpoint = self.contract.endpoints[operation]
        fields = {name for _, name, _, _ in Formatter().parse(endpoint.path) if name}
        if set(path_params) != fields:
            raise APIError(
                "input", "Path parameters do not match the operation contract."
            )
        safe = {}
        for key, value in path_params.items():
            if type(value) not in {str, int} or not re.fullmatch(
                r"[A-Za-z0-9_-]+", str(value)
            ):
                raise APIError("input", "Invalid path identifier.")
            safe[key] = quote(str(value), safe="")
        allowed = set(endpoint.required_query) | set(endpoint.optional_query)
        if endpoint.cursor_param:
            allowed.add(endpoint.cursor_param)
        if set(query) - allowed or set(endpoint.required_query) - set(query):
            raise APIError(
                "input", "Query parameters do not match the operation contract."
            )
        if any(type(value) not in {str, int} for value in query.values()):
            raise APIError("input", "Query values must be text or integer values.")
        url = self.contract.base_url.rstrip("/") + endpoint.path.format(**safe)
        return url

    def get(self, operation: str, *, path_params=None, query=None) -> APIResponse:
        """Request one JSON snapshot, with bounded retries and redirect refusal."""
        path_params, query = path_params or {}, query or {}
        url = self._request_parts(operation, path_params, query)
        if not self._key:
            raise APIError("configuration", "HTTP client is closed.")
        if self._clock() < self._next_allowed:
            raise APIError(
                "cooldown",
                "Wait before the next provider request.",
                self._next_allowed - self._clock(),
            )
        deadline = self._clock() + self.policy.operation_budget
        for attempt in range(self.policy.max_attempts):
            remaining = deadline - self._clock()
            if remaining <= 0:
                raise APIError(
                    "timeout",
                    "The provider operation exceeded its elapsed-time budget.",
                )
            self._next_allowed = self._clock() + self.policy.min_interval
            retry_after = None
            try:
                response = self._session.get(
                    url,
                    params=dict(query),
                    headers={
                        "Accept": "application/json",
                        **self.contract.static_headers,
                        self.contract.auth_header: self._key,
                    },
                    timeout=(
                        min(self.policy.connect_timeout, remaining),
                        min(self.policy.read_timeout, remaining),
                    ),
                    allow_redirects=False,
                    stream=True,
                )
                try:
                    status = response.status_code
                    if status == 429:
                        retry_after = self._retry_after(
                            response.headers.get("Retry-After")
                        )
                        if retry_after is not None:
                            self._next_allowed = max(
                                self._next_allowed, self._clock() + retry_after
                            )
                    if status in {429, 500, 502, 503, 504}:
                        error = APIError(
                            "rate_limit" if status == 429 else "upstream",
                            "Provider request is temporarily unavailable.",
                            retry_after,
                        )
                    elif status in {401, 403}:
                        raise APIError(
                            "authentication",
                            "Provider credentials or subscription were rejected.",
                        )
                    elif status == 404:
                        raise APIError(
                            "not_found",
                            "Provider did not return the requested resource.",
                        )
                    elif status != 200:
                        raise APIError(
                            "http", "Provider returned an unsupported HTTP response."
                        )
                    else:
                        content_type = (
                            response.headers.get("Content-Type", "")
                            .split(";")[0]
                            .strip()
                            .lower()
                        )
                        if (
                            content_type != "application/json"
                            and not content_type.endswith("+json")
                        ):
                            raise APIError("json", "Provider response is not JSON.")
                        body = bytearray()
                        for chunk in response.iter_content(chunk_size=8192):
                            body.extend(chunk)
                            if len(body) > self.policy.max_bytes:
                                raise APIError(
                                    "size",
                                    "Provider response exceeds the configured size limit.",
                                )
                            if self._clock() > deadline:
                                raise APIError(
                                    "timeout",
                                    "Provider response exceeded the elapsed-time budget.",
                                )
                        try:
                            data = json.loads(body)
                        except (ValueError, UnicodeError, RecursionError):
                            raise APIError(
                                "json", "Provider response contains invalid JSON."
                            ) from None
                        if not isinstance(data, (dict, list)):
                            raise APIError(
                                "shape",
                                "Provider JSON must contain an object or array.",
                            )
                        if isinstance(data, dict) and data.get("error"):
                            raise APIError(
                                "provider", "Provider returned an error payload."
                            )
                        quota = {
                            k.lower(): str(v)
                            for k, v in response.headers.items()
                            if k.lower()
                            in {
                                "x-ratelimit-requests-limit",
                                "x-ratelimit-requests-remaining",
                                "x-ratelimit-requests-reset",
                            }
                        }
                        return APIResponse(
                            data,
                            self.contract.provider,
                            self.contract.version,
                            operation,
                            datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                            str(
                                response.headers.get(
                                    "x-rapidapi-mock-response", "false"
                                )
                            ).lower()
                            == "true",
                            quota,
                        )
                finally:
                    response.close()
            except requests.exceptions.SSLError:
                raise APIError("tls", "Provider TLS verification failed.") from None
            except (
                requests.Timeout,
                requests.ConnectionError,
                requests.exceptions.ChunkedEncodingError,
            ):
                error = APIError("network", "Provider connection failed or timed out.")
            except requests.RequestException:
                raise APIError("network", "Provider request failed.") from None
            LOG.warning(
                "Provider attempt failed: operation=%s code=%s attempt=%s",
                operation,
                error.code,
                attempt + 1,
            )
            if attempt + 1 == self.policy.max_attempts:
                raise error from None
            delay = (
                retry_after
                if retry_after is not None
                else self.policy.retry_delay * (2**attempt)
            )
            delay = max(delay, self._next_allowed - self._clock())
            if delay > self.policy.max_retry_wait or self._clock() + delay >= deadline:
                raise error from None
            self._sleep(delay)
        raise APIError("network", "Provider request failed.")

    @staticmethod
    def _retry_after(value):
        """Parse bounded provider retry guidance without exposing response headers."""
        if value is None:
            return None
        try:
            result = float(value)
            return max(0, result) if math.isfinite(result) else None
        except ValueError:
            try:
                parsed = parsedate_to_datetime(value)
                return max(0, (parsed - datetime.now(UTC)).total_seconds())
            except (ValueError, TypeError, OverflowError):
                return None

    def pages(self, operation, *, path_params=None, query=None, max_pages=10):
        """Yield only explicitly configured cursor pages; reject loops/truncation."""
        if type(max_pages) is not int or not 1 <= max_pages <= 100:
            raise APIError("input", "Pagination must have a finite page limit.")
        endpoint = self.contract.endpoints.get(operation)
        if endpoint is None or not endpoint.cursor_param:
            raise APIError(
                "configuration", "No pagination is configured for this operation."
            )
        parameters, seen = dict(query or {}), set()
        deadline = self._clock() + self.policy.operation_budget
        for _ in range(max_pages):
            pause = max(0, self._next_allowed - self._clock())
            if self._clock() + pause >= deadline:
                raise APIError(
                    "timeout", "Pagination exceeded the elapsed-time budget."
                )
            if pause > self.policy.max_retry_wait:
                raise APIError(
                    "cooldown", "Pagination must wait before another request.", pause
                )
            if pause:
                self._sleep(pause)
            result = self.get(operation, path_params=path_params, query=parameters)
            items = _path(result.data, endpoint.items_path)
            if not isinstance(items, list):
                raise APIError("shape", "Paginated items must be an array.")
            cursor = _path(result.data, endpoint.next_cursor_path)
            if cursor is not None and cursor != "":
                if type(cursor) not in {str, int} or str(cursor) in seen:
                    raise APIError(
                        "pagination", "Provider returned an invalid or repeated cursor."
                    )
                seen.add(str(cursor))
            yield items, result
            if cursor is None or cursor == "":
                return
            parameters[endpoint.cursor_param] = cursor
        raise APIError(
            "pagination", "Pagination limit reached before documented completion."
        )
