"""Transport checks use injected HTTP doubles; no real API requests occur."""

import json
from dataclasses import replace

import pytest
import requests

from api.client import APIError, CricbuzzClient, Endpoint, HTTPPolicy, ProviderContract


class Response:
    def __init__(self, data=None, status=200, headers=None, raw=None):
        self.status_code = status
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self.raw = raw if raw is not None else json.dumps(data or {}).encode()
        self.closed = False

    def iter_content(self, chunk_size):
        yield self.raw

    def close(self):
        self.closed = True


class Session:
    def __init__(self, outcomes):
        self.outcomes, self.calls = list(outcomes), []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def close(self):
        pass


@pytest.fixture
def contract():
    return ProviderContract(
        "injected-test-provider",
        "test-v1",
        "https://fixture.example/api",
        "X-Test-Key",
        {
            "live_matches": Endpoint("/live"),
            "scorecard": Endpoint("/match/{match_id}"),
            "search": Endpoint("/search", required_query=("name",)),
            "history": Endpoint(
                "/history",
                cursor_param="cursor",
                items_path=("items",),
                next_cursor_path=("next",),
            ),
        },
        verified=True,
    )


def client(contract, outcomes, **policy):
    session = Session(outcomes)
    return CricbuzzClient(
        contract,
        "private-test-value",
        session=session,
        policy=HTTPPolicy(min_interval=0, retry_delay=0, **policy),
        sleep=lambda _: None,
    ), session


def test_success_headers_timeout_and_close(contract):
    response = Response({"items": []}, headers={"x-ratelimit-requests-remaining": "7"})
    api, session = client(contract, [response])
    result = api.get("scorecard", path_params={"match_id": "123"})
    url, options = session.calls[0]
    assert url == "https://fixture.example/api/match/123"
    assert options["allow_redirects"] is False and options["stream"] is True
    assert options["timeout"] == (3, 5)
    assert options["headers"]["X-Test-Key"] == "private-test-value"
    assert result.quota == {"x-ratelimit-requests-remaining": "7"}
    assert response.closed and not result.is_mock


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "authentication"),
        (403, "authentication"),
        (404, "not_found"),
        (302, "http"),
        (204, "http"),
        (400, "http"),
    ],
)
def test_nonretryable_statuses_safe(contract, status, code):
    response = Response({"secret": "private-test-value"}, status=status)
    api, session = client(contract, [response])
    with pytest.raises(APIError) as caught:
        api.get("live_matches")
    assert caught.value.code == code
    assert "private-test-value" not in str(caught.value)
    assert len(session.calls) == 1 and response.closed


@pytest.mark.parametrize(
    "failure",
    [
        requests.Timeout("private-test-value"),
        requests.ConnectionError("private-test-value"),
        Response(status=503),
    ],
)
def test_retry_then_success(contract, failure):
    api, session = client(contract, [failure, Response({"ok": True})])
    assert api.get("live_matches").data == {"ok": True}
    assert len(session.calls) == 2


def test_attempt_limit_and_safe_logging(contract, caplog):
    api, session = client(contract, [requests.Timeout("private-test-value")] * 3)
    with pytest.raises(APIError):
        api.get("live_matches")
    assert len(session.calls) == 3
    assert "private-test-value" not in caplog.text


def test_retry_after_does_not_sleep_for_a_long_interval(contract):
    api, session = client(
        contract, [Response(status=429, headers={"Retry-After": "90"})]
    )
    with pytest.raises(APIError) as caught:
        api.get("live_matches")
    assert caught.value.code == "rate_limit" and caught.value.retry_after == 90
    with pytest.raises(APIError, match="Wait"):
        api.get("live_matches")
    assert len(session.calls) == 1


@pytest.mark.parametrize(
    "response,code",
    [
        (
            Response(
                raw=b"<html>unavailable</html>", headers={"Content-Type": "text/html"}
            ),
            "json",
        ),
        (Response(raw=b"not-json"), "json"),
        (Response(raw=b"123"), "shape"),
        (Response({"error": True, "message": "private-test-value"}), "provider"),
        (Response(raw=b"{}" * 100), "size"),
    ],
)
def test_malformed_or_large_response(contract, response, code):
    api, _ = client(contract, [response], max_bytes=100)
    with pytest.raises(APIError) as caught:
        api.get("live_matches")
    assert caught.value.code == code and response.closed


def test_mock_provenance(contract):
    api, _ = client(contract, [Response(headers={"x-rapidapi-mock-response": "true"})])
    assert api.get("live_matches").is_mock


@pytest.mark.parametrize(
    "path",
    [
        "//other.example",
        "https://other.example",
        "/../private",
        "/%2fprivate",
        "/x?secret=1",
        "/{id!r}",
    ],
)
def test_bad_contract_paths_rejected(contract, path):
    bad = replace(contract, endpoints={"live_matches": Endpoint(path)})
    with pytest.raises(APIError):
        CricbuzzClient(bad, "private-test-value")


def test_unverified_contract_rejected(contract):
    with pytest.raises(APIError):
        CricbuzzClient(replace(contract, verified=False), "private-test-value")


@pytest.mark.parametrize(
    "params",
    [
        {"match_id": "../123"},
        {"match_id": "https://other.example"},
        {"match_id": True},
        {},
    ],
)
def test_bad_identifiers_never_make_a_request(contract, params):
    api, session = client(contract, [])
    with pytest.raises(APIError):
        api.get("scorecard", path_params=params)
    assert session.calls == []


def test_required_and_extra_query_parameters(contract):
    api, session = client(contract, [])
    with pytest.raises(APIError):
        api.get("search")
    with pytest.raises(APIError):
        api.get("live_matches", query={"unknown": 1})
    assert session.calls == []


def test_pagination_ends_on_documented_null(contract):
    api, session = client(
        contract,
        [Response({"items": [1], "next": "a"}), Response({"items": [2], "next": None})],
    )
    assert [items for items, _ in api.pages("history")] == [[1], [2]]
    assert session.calls[1][1]["params"] == {"cursor": "a"}


def test_repeated_cursor_is_rejected(contract):
    api, _ = client(
        contract,
        [Response({"items": [1], "next": "a"}), Response({"items": [2], "next": "a"})],
    )
    with pytest.raises(APIError, match="repeated"):
        list(api.pages("history"))


def test_pagination_limit_is_not_silent_completion(contract):
    api, _ = client(contract, [Response({"items": [1], "next": "a"})])
    with pytest.raises(APIError, match="limit"):
        list(api.pages("history", max_pages=1))


def test_no_guessed_pagination(contract):
    api, _ = client(contract, [])
    with pytest.raises(APIError, match="pagination"):
        list(api.pages("live_matches"))


def test_tls_failure_not_retried(contract):
    api, session = client(
        contract, [requests.exceptions.SSLError("private-test-value")]
    )
    with pytest.raises(APIError) as caught:
        api.get("live_matches")
    assert caught.value.code == "tls" and len(session.calls) == 1
