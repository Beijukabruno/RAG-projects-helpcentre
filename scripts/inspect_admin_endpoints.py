#!/usr/bin/env python3

"""Inspect the admin API and save endpoint outputs for UI requirements work.

This script is intentionally read-only by default. It logs in, calls the
documented admin GET endpoints, prints a compact summary to stdout, and saves
the raw responses to disk so the outputs can be reviewed later when defining
the admin UI.

Usage examples:

    python3 scripts/inspect_admin_endpoints.py
    python3 scripts/inspect_admin_endpoints.py --base-url https://helpcentre-dsi-mdr.emergentai.ug
    python3 scripts/inspect_admin_endpoints.py --project-id cervical_cancer --audience clinicians
    python3 scripts/inspect_admin_endpoints.py --token "$ADMIN_TOKEN"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

from dotenv import load_dotenv


load_dotenv()


REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOYED_BASE_URL = "https://helpcentre-dsi-mdr.emergentai.ug"


DEFAULT_BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
DEFAULT_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASS", "change-me-immediately")
DEFAULT_PROJECT_ID = os.getenv("PROJECT_ID", "tb")
DEFAULT_AUDIENCE = os.getenv("AUDIENCE", "general")
DEFAULT_OUTPUT_DIR = os.getenv(
    "ADMIN_INSPECT_OUTPUT_DIR",
    str(REPO_ROOT / "reports" / "admin-endpoint-inspection"),
)


@dataclass
class EndpointResult:
    label: str
    method: str
    path: str
    status_code: int
    content_type: str
    body: Any
    raw_text: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect admin endpoints and save their outputs.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    parser.add_argument("--email", default=DEFAULT_ADMIN_EMAIL, help="Admin email for login")
    parser.add_argument("--password", default=DEFAULT_ADMIN_PASSWORD, help="Admin password for login")
    parser.add_argument("--token", default=os.getenv("ADMIN_TOKEN"), help="Optional bearer token to skip login")
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID, help="Project id to inspect")
    parser.add_argument("--audience", default=DEFAULT_AUDIENCE, help="Audience for project-scoped log/source routes")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for saved responses")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    return parser


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def resolve_output_dir(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def resolve_api_base_url(candidate_base_url: str, timeout: int) -> str:
    candidates = [normalize_base_url(candidate_base_url)]
    fallback = normalize_base_url(DEPLOYED_BASE_URL)
    if fallback not in candidates:
        candidates.append(fallback)

    for candidate in candidates:
        health_result = make_request("GET", f"{candidate}/health", timeout=timeout)
        if health_result.status_code > 0:
            if candidate != normalize_base_url(candidate_base_url):
                print(f"Using fallback API base URL: {candidate}")
            return candidate
        print(f"Unreachable API base URL: {candidate}")

    raise RuntimeError(
        "Unable to reach any API base URL. Pass --base-url to a running instance or start the local service."
    )


def pretty_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)


def parse_response_body(content_type: str, raw: bytes) -> tuple[Any, str]:
    text = raw.decode("utf-8", errors="replace")
    if "application/json" in content_type or text.lstrip().startswith(("{", "[")):
        try:
            return json.loads(text), text
        except json.JSONDecodeError:
            return text, text
    return text, text


def make_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: int = 30,
) -> EndpointResult:
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)

    data = None
    if json_body is not None:
        request_headers["Content-Type"] = "application/json"
        data = json.dumps(json_body).encode("utf-8")

    req = request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            content_type = resp.headers.get("Content-Type", "")
            body, text = parse_response_body(content_type, raw)
            return EndpointResult(
                label="",
                method=method,
                path=url,
                status_code=resp.getcode(),
                content_type=content_type,
                body=body,
                raw_text=text,
            )
    except error.HTTPError as exc:
        raw = exc.read()
        content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
        body, text = parse_response_body(content_type, raw)
        return EndpointResult(
            label="",
            method=method,
            path=url,
            status_code=exc.code,
            content_type=content_type,
            body=body,
            raw_text=text,
        )
    except error.URLError as exc:
        return EndpointResult(
            label="",
            method=method,
            path=url,
            status_code=0,
            content_type="",
            body=None,
            raw_text=str(exc),
        )


def login(base_url: str, email: str, password: str, timeout: int) -> tuple[str | None, dict[str, Any] | None]:
    result = make_request(
        "POST",
        f"{base_url}/admin/auth/login",
        json_body={"email": email, "password": password},
        timeout=timeout,
    )
    if result.status_code != 200 or not isinstance(result.body, dict):
        print(f"[auth/login] failed ({result.status_code})")
        print(result.raw_text)
        return None, result.body if isinstance(result.body, dict) else None

    token = result.body.get("access_token")
    if not token:
        print("[auth/login] response did not include access_token")
        return None, result.body
    return str(token), result.body


def describe_body(body: Any) -> str:
    if isinstance(body, dict):
        keys = ", ".join(sorted(body.keys()))
        return f"dict(keys=[{keys}])"
    if isinstance(body, list):
        return f"list(len={len(body)})"
    if isinstance(body, str):
        return f"text(len={len(body)})"
    return type(body).__name__


def save_result(output_dir: Path, result: EndpointResult, suffix: str) -> Path:
    safe_name = result.label.replace(" ", "_").replace("/", "_").replace(":", "_").lower()
    file_name = f"{safe_name}_{suffix}"
    if "csv" in result.content_type.lower() or result.path.endswith("csv"):
        file_name += ".csv"
        content = result.raw_text
    elif isinstance(result.body, (dict, list)):
        file_name += ".json"
        content = pretty_json(result.body)
    else:
        file_name += ".txt"
        content = result.raw_text

    path = output_dir / file_name
    path.write_text(content, encoding="utf-8")
    return path


def probe(
    base_url: str,
    token: str,
    output_dir: Path,
    timeout: int,
    project_id: str,
    audience: str,
) -> list[EndpointResult]:
    headers = {"Authorization": f"Bearer {token}"}

    endpoints: list[tuple[str, str, dict[str, Any] | None, str]] = [
        ("GET", "/health", None, "health"),
        ("GET", "/ready", None, "ready"),
        ("GET", "/admin/auth/me", None, "admin_auth_me"),
        ("GET", "/admin/users", None, "admin_users"),
        ("GET", "/admin/projects", None, "admin_projects"),
        ("GET", f"/admin/projects/{project_id}", None, "admin_project_detail"),
        ("GET", f"/admin/projects/{project_id}/admins", None, "admin_project_admins"),
        ("GET", f"/admin/projects/{project_id}/knowledge-base?audience={audience}", None, "admin_kb_sources"),
        ("GET", "/admin/overview", None, "admin_platform_overview"),
        ("GET", f"/admin/projects/{project_id}/overview", None, "admin_project_overview"),
        ("GET", "/admin/audit-logs?limit=10", None, "admin_audit_logs"),
        ("GET", f"/admin/projects/{project_id}/audit-logs?limit=10", None, "admin_project_audit_logs"),
        ("GET", "/admin/toxicity-feed?limit=10", None, "admin_toxicity_feed"),
        ("GET", "/admin/last-records?n=10", None, "admin_last_records"),
        ("GET", f"/admin/projects/{project_id}/last-records?n=10&audience={audience}", None, "admin_project_last_records"),
        ("GET", "/admin/last-records-csv?n=10", None, "admin_last_records_csv"),
        ("GET", f"/admin/projects/{project_id}/last-records-csv?n=10&audience={audience}", None, "admin_project_last_records_csv"),
    ]

    results: list[EndpointResult] = []
    for method, path, json_body, label in endpoints:
        url = f"{base_url}{path}"
        result = make_request(method, url, headers=headers, json_body=json_body, timeout=timeout)
        result.label = label
        results.append(result)
        saved_path = save_result(output_dir, result, label)
        print(f"[{label}] {method} {path} -> {result.status_code} | {describe_body(result.body)} | saved: {saved_path}")
        if result.status_code >= 400:
            print(result.raw_text)

    return results


def write_summary(output_dir: Path, base_url: str, project_id: str, audience: str, results: list[EndpointResult]) -> Path:
    summary = {
        "base_url": base_url,
        "project_id": project_id,
        "audience": audience,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "results": [
            {
                "label": result.label,
                "method": result.method,
                "path": result.path,
                "status_code": result.status_code,
                "content_type": result.content_type,
                "body_type": type(result.body).__name__,
            }
            for result in results
        ],
    }
    path = output_dir / "summary.json"
    path.write_text(pretty_json(summary), encoding="utf-8")
    return path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    base_url = resolve_api_base_url(args.base_url, args.timeout)
    output_root = resolve_output_dir(args.output_dir)
    run_dir = output_root / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ensure_dir(run_dir)

    print(f"Base URL: {base_url}")
    print(f"Output directory: {run_dir}")
    print(f"Project: {args.project_id}")
    print(f"Audience: {args.audience}")

    token = args.token
    login_payload = None
    if not token:
        token, login_payload = login(base_url, args.email, args.password, args.timeout)
        if not token:
            return 1
        login_path = run_dir / "admin_auth_login.json"
        login_path.write_text(pretty_json(login_payload), encoding="utf-8")
        print(f"[auth/login] saved: {login_path}")
    else:
        print("Using provided bearer token; skipping login.")

    auth_me = make_request(
        "GET",
        f"{base_url}/admin/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=args.timeout,
    )
    auth_me.label = "admin_auth_me"
    auth_me_path = save_result(run_dir, auth_me, "admin_auth_me")
    print(f"[admin/auth/me] GET /admin/auth/me -> {auth_me.status_code} | {describe_body(auth_me.body)} | saved: {auth_me_path}")
    if auth_me.status_code >= 400:
        print(auth_me.raw_text)

    results = probe(base_url, token, run_dir, args.timeout, args.project_id, args.audience)
    results.insert(0, auth_me)
    summary_path = write_summary(run_dir, base_url, args.project_id, args.audience, results)
    print(f"Summary saved: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())