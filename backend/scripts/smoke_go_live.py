#!/usr/bin/env python3
"""
Go-live / Staging smoke checks against a running GridCheck API.

Kein echter Stripe-Charge: Billing-Status wird nur gelesen. Fuer Checkout/Webhooks
Stripe Testmode (sk_test_, pk_test_, whsec_) verwenden.

Beispiel:
  python scripts/smoke_go_live.py --base-url https://api-staging.example.com \\
    --email smoke@example.com --password 'Passwort123!'
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import httpx

ANALYZE_PAYLOAD: dict[str, Any] = {
    "nennspannung": 20.0,
    "leistung_mw": 1.2,
    "leitungstyp": "NA2XS2Y240",
    "entfernung_km": 2.0,
    "anschlussart": "Einspeisung",
    "plz": "10115",
    "anlagentyp": "PV",
}


def _ok(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"[OK] {label}{suffix}")


def _fail(label: str, detail: str) -> None:
    print(f"[FAIL] {label}: {detail}", file=sys.stderr)


def _register_probe(client: httpx.Client, url: str, label: str) -> bool:
    payload = {"email": "smoke-probe@example.com", "password": "short", "role": "projektierer"}
    try:
        res = client.post(url, json=payload)
        if res.status_code in (400, 422):
            _ok(label, f"HTTP {res.status_code} (Route erreichbar)")
            return True
        if res.status_code == 409:
            _ok(label, "HTTP 409 (E-Mail existiert — Route OK)")
            return True
        if res.status_code == 503:
            _fail(label, "HTTP 503 — DB/Migration? alembic upgrade head")
            return False
        res.raise_for_status()
        _ok(label, f"HTTP {res.status_code}")
        return True
    except Exception as exc:
        _fail(label, str(exc))
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="GridCheck API smoke checks (staging/go-live).")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend root URL ohne trailing slash")
    parser.add_argument(
        "--frontend-url",
        help="Optional: Vercel-URL; prueft /api/backend/health und /api/auth/register",
    )
    parser.add_argument("--email", help="Optional: Login fuer geschuetzte Endpoints")
    parser.add_argument("--password", help="Passwort zu --email")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    frontend = args.frontend_url.rstrip("/") if args.frontend_url else None
    failures = 0
    token: str | None = None

    with httpx.Client(timeout=args.timeout, follow_redirects=True) as client:
        try:
            health = client.get(f"{base}/health")
            health.raise_for_status()
            body = health.json()
            if body.get("status") != "ok":
                raise ValueError(f"unexpected body: {body!r}")
            _ok("GET /health", f"version={body.get('version', '?')}")
        except Exception as exc:
            _fail("GET /health", str(exc))
            failures += 1

        if not _register_probe(client, f"{base}/api/v1/auth/register", "POST /api/v1/auth/register (probe)"):
            failures += 1

        if frontend:
            try:
                fh = client.get(f"{frontend}/api/backend/health")
                fh.raise_for_status()
                _ok("Frontend proxy /api/backend/health", f"HTTP {fh.status_code}")
            except Exception as exc:
                _fail("Frontend proxy /api/backend/health", str(exc))
                failures += 1
            for path in ("/api/auth/register", "/api/backend/api/v1/auth/register"):
                if not _register_probe(
                    client,
                    f"{frontend}{path}",
                    f"POST {path} (via Frontend)",
                ):
                    failures += 1

        if args.email:
            if not args.password:
                _fail("login", "--password fehlt zu --email")
                return 1
            try:
                login = client.post(
                    f"{base}/api/v1/auth/login",
                    json={"email": args.email, "password": args.password},
                )
                login.raise_for_status()
                token = login.json().get("access_token")
                if not token:
                    raise ValueError("access_token fehlt in Login-Response")
                _ok("POST /api/v1/auth/login")
            except Exception as exc:
                _fail("POST /api/v1/auth/login", str(exc))
                failures += 1
        else:
            print("[SKIP] Login — keine --email/--password gesetzt")

        headers = {"Authorization": f"Bearer {token}"} if token else {}

        if token:
            try:
                billing = client.get(f"{base}/api/v1/billing/status", headers=headers)
                billing.raise_for_status()
                data = billing.json()
                stripe_ready = data.get("stripe_configured", data.get("stripe_readiness"))
                _ok(
                    "GET /api/v1/billing/status",
                    f"plan_tier={data.get('plan_tier')} stripe_configured={stripe_ready}",
                )
            except Exception as exc:
                _fail("GET /api/v1/billing/status", str(exc))
                failures += 1

            try:
                analyze = client.post(f"{base}/api/v1/analyze", headers=headers, json=ANALYZE_PAYLOAD)
                if analyze.status_code not in (200, 422):
                    analyze.raise_for_status()
                if analyze.status_code == 200:
                    summary = analyze.json().get("fazit", {}).get("entscheidung", "?")
                    _ok("POST /api/v1/analyze", f"entscheidung={summary}")
                else:
                    detail = analyze.json().get("detail", analyze.text[:200])
                    _ok("POST /api/v1/analyze", f"422 (fachliche Validierung): {json.dumps(detail)[:120]}")
            except Exception as exc:
                _fail("POST /api/v1/analyze", str(exc))
                failures += 1

            try:
                history = client.get(f"{base}/api/v1/history", headers=headers)
                history.raise_for_status()
                items = history.json()
                count = len(items) if isinstance(items, list) else "?"
                _ok("GET /api/v1/history", f"projects={count}")
            except Exception as exc:
                _fail("GET /api/v1/history", str(exc))
                failures += 1

            try:
                pdf = client.post(
                    f"{base}/api/v2/reports/projektierer?format=pdf",
                    headers=headers,
                    json={"analyze_request": ANALYZE_PAYLOAD},
                )
                if pdf.status_code == 422:
                    detail = pdf.json().get("detail", pdf.text[:300])
                    code = detail.get("code") if isinstance(detail, dict) else None
                    if code == "REPORT_PDF_QUALITY_FAILED":
                        raise ValueError(f"quality gate: {detail}")
                    _ok(
                        "POST /api/v2/reports/projektierer?format=pdf",
                        f"422 (fachlich): {json.dumps(detail)[:120]}",
                    )
                else:
                    pdf.raise_for_status()
                    if not pdf.headers.get("content-type", "").startswith("application/pdf"):
                        raise ValueError(f"unexpected content-type: {pdf.headers.get('content-type')}")
                    if not pdf.content.startswith(b"%PDF"):
                        raise ValueError("response is not a PDF")
                    _ok(
                        "POST /api/v2/reports/projektierer?format=pdf",
                        f"bytes={len(pdf.content)}",
                    )
            except Exception as exc:
                _fail("POST /api/v2/reports/projektierer?format=pdf", str(exc))
                failures += 1
        else:
            print("[SKIP] billing / analyze / history / pdf — Login erforderlich")

    if failures:
        print(f"\n{failures} Check(s) fehlgeschlagen.", file=sys.stderr)
        return 1
    print("\nAlle Smoke-Checks bestanden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
