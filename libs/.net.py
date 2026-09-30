import json
import urllib.error
import urllib.request
from typing import Any


# Default timeout (seconds) for every request made through this module, used whenever
# the GBN side passes 0 or a negative number for "no timeout given".
_DEFAULT_TIMEOUT = 15.0


def _do_request(method: str, url: str, headers: dict, body, timeout: float) -> dict:
    """Core of every request below. Never raises for network-level failures (DNS,
    timeout, connection refused, TLS errors, ...) — those come back as a normal
    response dict with ok=False and an error message, so GBN scripts can check
    `.ok` the way they'd check a status code, instead of needing try/catch for
    something as ordinary as a flaky connection. A malformed URL/method, or an
    unrepresentable non-string body, raises normally (a real programming mistake).
    """
    effective_timeout = timeout if timeout and timeout > 0 else _DEFAULT_TIMEOUT
    data = body.encode("utf-8") if isinstance(body, str) else body
    request = urllib.request.Request(url, data=data, headers=dict(headers or {}), method=method)

    try:
        with urllib.request.urlopen(request, timeout=effective_timeout) as response:
            raw = response.read()
            return {
                "ok": True,
                "status": response.status,
                "headers": dict(response.headers.items()),
                "body": raw.decode("utf-8", errors="replace"),
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        # A real HTTP response with an error status code (404, 500, ...) — still a
        # normal, complete response, not a connectivity failure, so ok reflects the
        # 2xx/3xx-vs-not split rather than "did a response come back at all".
        raw = exc.read()
        return {
            "ok": False,
            "status": exc.code,
            "headers": dict(exc.headers.items()) if exc.headers else {},
            "body": raw.decode("utf-8", errors="replace") if raw else "",
            "error": f"HTTP {exc.code}: {exc.reason}",
        }
    except urllib.error.URLError as exc:
        # DNS failure, connection refused, timeout, TLS error, ... — no response at all.
        return {"ok": False, "status": 0, "headers": {}, "body": "", "error": str(exc.reason)}
    except (TimeoutError, OSError) as exc:
        return {"ok": False, "status": 0, "headers": {}, "body": "", "error": str(exc)}


def http_request(method: str, url: str, headers: dict, body: str, timeout: float) -> dict:
    return _do_request(method.upper(), url, headers, body, timeout)


def http_get(url: str, headers: dict, timeout: float) -> dict:
    return _do_request("GET", url, headers, None, timeout)


def http_post(url: str, body: str, headers: dict, timeout: float) -> dict:
    return _do_request("POST", url, headers, body, timeout)


def http_put(url: str, body: str, headers: dict, timeout: float) -> dict:
    return _do_request("PUT", url, headers, body, timeout)


def http_delete(url: str, headers: dict, timeout: float) -> dict:
    return _do_request("DELETE", url, headers, None, timeout)


def http_post_json(url: str, data: dict, headers: dict, timeout: float) -> dict:
    merged_headers = dict(headers or {})
    merged_headers.setdefault("Content-Type", "application/json")
    return _do_request("POST", url, merged_headers, json.dumps(data), timeout)


def url_encode(text: str) -> str:
    import urllib.parse
    return urllib.parse.quote(text, safe="")
