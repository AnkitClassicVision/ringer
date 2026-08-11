"""Closed, typed dispatch for non-appointment EyeCloud reads.

The public request selects a stable operation id, never a CLI command or flag.
Every accepted argument is rebuilt from the checked-in capability manifest.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import time
from pathlib import Path


class QueryError(ValueError):
    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code = code
        self.status = status


def load_manifest(path: str | None = None) -> dict:
    manifest_path = Path(
        path
        or os.environ.get("ECP_CAPABILITY_MANIFEST", "")
        or Path(__file__).with_name("eyecloud_capabilities.v1.json")
    )
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("schema_version") != "1":
        raise RuntimeError("unsupported capability manifest schema")
    return manifest


def _clean_template(value):
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("{{") and value.endswith("}}"):
            return None
    return value


def _validate_value(name: str, value, rule: dict):
    kind = rule["type"]
    if kind == "string":
        if not isinstance(value, (str, int)):
            raise QueryError("invalid_parameter")
        value = str(value).strip()
        if not value or len(value) > int(rule.get("max_length", 200)):
            raise QueryError("invalid_parameter")
        if rule.get("format") == "numeric" and not value.isdigit():
            raise QueryError("invalid_parameter")
        if value.startswith("-"):
            raise QueryError("invalid_parameter")
        return value
    if kind == "boolean":
        if not isinstance(value, bool):
            raise QueryError("invalid_parameter")
        return value
    raise QueryError("invalid_manifest", 500)


def _cursor_key(secret: str) -> bytes:
    return hashlib.sha256(("eyecloud-query-cursor:" + secret).encode()).digest()


def _params_digest(params: dict) -> str:
    normalized = json.dumps(params, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(normalized).hexdigest()


def _cursor_context(
    *,
    version: str,
    tenant: str,
    principal: str,
    operation: str,
    params_digest: str,
    projection: str,
    limit: int,
) -> dict:
    return {
        "version": version,
        "tenant": tenant,
        "principal": principal,
        "operation": operation,
        "params_digest": params_digest,
        "projection": projection,
        "limit": limit,
    }


def encode_cursor(context: dict, offset: int, secret: str, expires_at: int | None = None) -> str:
    raw = json.dumps(
        {
            **context,
            "offset": offset,
            "expires_at": expires_at or int(time.time()) + 300,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    signature = hmac.new(_cursor_key(secret), raw, hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(raw + signature).decode().rstrip("=")


def decode_cursor(cursor: str, context: dict, secret: str) -> int:
    if not cursor:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        packed = base64.urlsafe_b64decode(padded.encode())
        raw, supplied = packed[:-16], packed[-16:]
        expected = hmac.new(_cursor_key(secret), raw, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(supplied, expected):
            raise ValueError
        value = json.loads(raw)
        if any(value.get(key) != expected for key, expected in context.items()):
            raise ValueError
        if int(value["expires_at"]) < int(time.time()):
            raise ValueError
        offset = int(value["offset"])
        if offset < 0:
            raise ValueError
        return offset
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise QueryError("invalid_cursor") from None


class OperationRateLimiter:
    """Atomic file-backed limiter for the current single-task deployment.

    SQLite serializes writers across gateway processes. Errors fail closed.
    The deployment is intentionally fixed at one ECS task; sharing this file
    across multiple tasks is outside the release boundary.
    """

    def __init__(self, path: str | None = None):
        self.path = path or os.environ.get(
            "ECP_QUERY_RATE_LIMIT_DB",
            "/tmp/cvc-booking-gateway-query-rate-limit.sqlite3",
        )

    def check(self, key: tuple[str, str, str], per_minute: int) -> None:
        now = time.time()
        key_hash = hashlib.sha256("\0".join(key).encode()).hexdigest()
        try:
            with sqlite3.connect(self.path, timeout=5, isolation_level=None) as db:
                db.execute("PRAGMA busy_timeout = 5000")
                db.execute(
                    "CREATE TABLE IF NOT EXISTS rate_events "
                    "(key_hash TEXT NOT NULL, occurred REAL NOT NULL)"
                )
                db.execute("BEGIN IMMEDIATE")
                db.execute("DELETE FROM rate_events WHERE occurred <= ?", (now - 60,))
                count = db.execute(
                    "SELECT COUNT(*) FROM rate_events WHERE key_hash = ?",
                    (key_hash,),
                ).fetchone()[0]
                if count >= per_minute:
                    db.execute("ROLLBACK")
                    raise QueryError("rate_limited", 429)
                db.execute(
                    "INSERT INTO rate_events(key_hash, occurred) VALUES (?, ?)",
                    (key_hash, now),
                )
                db.execute("COMMIT")
        except QueryError:
            raise
        except (OSError, sqlite3.Error):
            raise QueryError("rate_limiter_unavailable", 503) from None


RATE_LIMITER = OperationRateLimiter()


def prepare_query(
    request: dict,
    *,
    cli: str,
    principal: str,
    tenant: str,
    release_gate: str,
    cursor_secret: str,
    manifest: dict | None = None,
) -> dict:
    if not isinstance(request, dict):
        raise QueryError("invalid_request")
    allowed_top = {"operation", "reason", "params", "projection", "limit", "cursor"}
    if set(request) - allowed_top:
        raise QueryError("unknown_field")

    operation_id = _clean_template(request.get("operation"))
    if not isinstance(operation_id, str):
        raise QueryError("unknown_operation")
    operation = (manifest or load_manifest()).get("operations", {}).get(operation_id)
    if not operation or operation.get("effect") != "read":
        raise QueryError("unknown_operation")
    if operation.get("release_state") == "blocked":
        raise QueryError("operation_blocked", 403)
    if operation.get("release_state") == "test_only" and release_gate != "SYNTHETIC_TEST_ONLY":
        raise QueryError("operation_blocked", 403)
    if principal not in operation.get("allowed_principals", []):
        raise QueryError("principal_not_allowed", 403)

    reason = _clean_template(request.get("reason"))
    if reason not in operation.get("reason_codes", []):
        raise QueryError("invalid_reason")
    projection = _clean_template(request.get("projection")) or operation["default_projection"]
    if projection not in operation.get("projections", {}):
        raise QueryError("invalid_projection")

    params = request.get("params") or {}
    if not isinstance(params, dict):
        raise QueryError("invalid_parameters")
    schema = operation["request_schema"]["properties"]
    if set(params) - set(schema):
        raise QueryError("unknown_parameter")
    clean_params = {}
    for name, rule in schema.items():
        value = _clean_template(params.get(name))
        if value is None:
            if name in operation["request_schema"].get("required", []):
                raise QueryError("missing_parameter")
            continue
        clean_params[name] = _validate_value(name, value, rule)

    max_rows = int(operation["limits"]["max_rows"])
    requested_limit = request.get("limit", max_rows)
    if isinstance(requested_limit, bool) or not isinstance(requested_limit, int):
        raise QueryError("invalid_limit")
    if requested_limit < 1 or requested_limit > max_rows:
        raise QueryError("invalid_limit")
    params_digest = _params_digest(clean_params)
    cursor_context = _cursor_context(
        version=(manifest or load_manifest())["schema_version"],
        tenant=tenant,
        principal=principal,
        operation=operation_id,
        params_digest=params_digest,
        projection=projection,
        limit=requested_limit,
    )
    cursor = _clean_template(request.get("cursor")) or ""
    if not isinstance(cursor, str):
        raise QueryError("invalid_cursor")
    offset = decode_cursor(cursor, cursor_context, cursor_secret)

    argv = [cli, *operation["cli_adapter"], "--agent", "--reason", f"bland-{reason}"]
    for name, rule in schema.items():
        if name not in clean_params:
            continue
        value = clean_params[name]
        if rule["type"] == "boolean":
            if value:
                argv.append(rule["flag"])
        else:
            argv.extend([rule["flag"], value])

    RATE_LIMITER.check(
        (tenant, principal, operation_id),
        int(operation["limits"]["rate_per_minute"]),
    )
    return {
        "operation_id": operation_id,
        "operation": operation,
        "argv": argv,
        "projection": projection,
        "limit": requested_limit,
        "offset": offset,
        "cursor_context": cursor_context,
        "timeout_s": int(operation["limits"]["timeout_seconds"]),
    }


def _project(value, allowed_fields: set[str]):
    if isinstance(value, list):
        return [_project(item, allowed_fields) for item in value]
    if isinstance(value, dict):
        return {
            key: _project(item, allowed_fields)
            for key, item in value.items()
            if key in allowed_fields
        }
    return value


def render_query_result(prepared: dict, raw_result, cursor_secret: str) -> dict:
    operation = prepared["operation"]
    projection = operation["projections"][prepared["projection"]]
    allowed = set(projection["fields"])
    withheld = list(projection.get("sensitive_withheld", []))

    list_key = operation["response_schema"].get("list_key")
    if isinstance(raw_result, list):
        items = raw_result
        envelope = None
    elif list_key and isinstance(raw_result, dict) and isinstance(raw_result.get(list_key), list):
        items = raw_result[list_key]
        envelope = raw_result
    else:
        items = None
        envelope = raw_result

    capped = False
    next_cursor = ""
    if items is not None:
        start = prepared["offset"]
        end = start + prepared["limit"]
        selected = items[start:end]
        capped = end < len(items)
        if capped:
            next_cursor = encode_cursor(prepared["cursor_context"], end, cursor_secret)
        projected_items = _project(selected, allowed)
        if envelope is None:
            result = projected_items
        else:
            result = _project(envelope, allowed)
            result[list_key] = projected_items
        count = len(projected_items)
    else:
        result = _project(envelope, allowed)
        count = 1 if result else 0

    max_bytes = int(operation["limits"]["max_response_bytes"])
    while items is not None and result and len(json.dumps(result).encode()) > max_bytes:
        capped = True
        if isinstance(result, list):
            result.pop()
            count = len(result)
        else:
            result[list_key].pop()
            count = len(result[list_key])
        next_cursor = encode_cursor(
            prepared["cursor_context"],
            prepared["offset"] + count,
            cursor_secret,
        )
    if len(json.dumps(result).encode()) > max_bytes:
        raise QueryError("response_too_large", 502)

    return {
        "ok": True,
        "operation": prepared["operation_id"],
        "schema_version": "1",
        "result": result,
        "meta": {
            "count": count,
            "capped": capped,
            "next_cursor": next_cursor,
            "sensitive_withheld": withheld,
        },
    }
