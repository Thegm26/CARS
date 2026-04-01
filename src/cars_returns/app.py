from __future__ import annotations

from http import cookies
import json
import os
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.util import setup_testing_defaults

from cars_returns.auth import AuthenticationError, AuthorizationError, SessionAuth
from cars_returns.db import initialize_database, seed_demo_data
from cars_returns.models import ReturnRequestItem
from cars_returns.repository import SQLiteRepository
from cars_returns.service import DomainError
from cars_returns.service import ReturnsService
from cars_returns.templates import (
    dashboard_page,
    login_page,
    manager_queue_page,
    order_detail_page,
    render_page,
    return_detail_page,
)


def create_app(*, db_path: str | None = None, seed_demo: bool = True):
    resolved_db_path = db_path or os.environ.get(
        "CARS_RETURNS_DB_PATH",
        str(Path(__file__).resolve().parents[2] / "var" / "cars_returns.db"),
    )
    initialize_database(resolved_db_path)
    if seed_demo:
        seed_demo_data(resolved_db_path)
    repository = SQLiteRepository(resolved_db_path)
    auth = SessionAuth(repository)
    service = ReturnsService(repository)

    def app(environ, start_response):
        setup_testing_defaults(environ)
        method = environ["REQUEST_METHOD"]
        path = environ["PATH_INFO"]
        body_bytes = environ["wsgi.input"].read(int(environ.get("CONTENT_LENGTH") or "0"))
        form = parse_qs(body_bytes.decode("utf-8")) if body_bytes else {}
        flash = parse_qs(environ.get("QUERY_STRING", "")).get("flash", [None])[0]

        try:
            if path == "/health" and method == "GET":
                return _json(start_response, 200, {"status": "ok"})
            if path == "/" and method == "GET":
                if _session_id(environ):
                    return _redirect(start_response, "/app")
                return _redirect(start_response, "/login")
            if path == "/login" and method == "GET":
                return _html(start_response, 200, login_page(error=flash))
            if path == "/login" and method == "POST":
                session_id, _ = auth.login(_first(form, "email"), _first(form, "password"))
                return _redirect(
                    start_response,
                    "/app",
                    headers=[("Set-Cookie", _session_cookie(session_id))],
                )
            if path == "/logout" and method == "POST":
                auth.logout(_session_id(environ))
                return _redirect(
                    start_response,
                    "/login",
                    headers=[("Set-Cookie", _expired_session_cookie())],
                )

            user = auth.authenticate_request(environ.get("HTTP_COOKIE"))

            if path == "/app" and method == "GET":
                html = dashboard_page(
                    user,
                    service.list_orders_for_user(user),
                    service.list_return_requests_for_user(user),
                )
                return _html(start_response, 200, html)
            if path.startswith("/orders/") and method == "GET":
                order_id = path.split("/")[2]
                order = service.get_order_for_user(user, order_id)
                html = order_detail_page(
                    user,
                    order,
                    return_eligible=service.is_return_eligible(order),
                )
                return _html(start_response, 200, html)
            if path.startswith("/orders/") and path.endswith("/returns") and method == "POST":
                order_id = path.split("/")[2]
                order = service.get_order_for_user(user, order_id)
                items = []
                for item in order.items:
                    qty = int(_first(form, f"qty_{item.sku}", "0") or "0")
                    if qty > 0:
                        items.append(ReturnRequestItem(sku=item.sku, quantity=qty))
                request = service.create_return_request(
                    user,
                    order_id,
                    items,
                    notes=_first(form, "notes"),
                )
                return _redirect(start_response, f"/returns/{request.id}")
            if path.startswith("/returns/") and method == "GET":
                request_id = path.split("/")[2]
                request = service.get_return_request_for_user(user, request_id)
                html = return_detail_page(
                    user,
                    request,
                    service.calculate_refund_total(request.id),
                    service.list_audit_events(user, request.id),
                    can_review=user.role == "support_manager",
                )
                return _html(start_response, 200, html)
            if path.startswith("/returns/") and path.endswith("/approve") and method == "POST":
                request_id = path.split("/")[2]
                request = service.approve_return_request(user, request_id)
                return _redirect(start_response, f"/returns/{request.id}")
            if path.startswith("/returns/") and path.endswith("/reject") and method == "POST":
                request_id = path.split("/")[2]
                request = service.reject_return_request(user, request_id)
                return _redirect(start_response, f"/returns/{request.id}")
            if path == "/returns/bulk-approve" and method == "POST":
                payload = service.bulk_approve_return_requests(
                    user,
                    form.get("request_ids", []),
                )
                return _json(start_response, 200, payload)
            if path == "/manager/queue" and method == "GET":
                html = manager_queue_page(user, service.list_pending_requests_for_review(user))
                return _html(start_response, 200, html)
            return _html(start_response, 404, render_page("Not Found", "<p>The page does not exist.</p>", user=user))
        except AuthenticationError as exc:
            if path.startswith("/login"):
                return _html(start_response, 401, login_page(error=str(exc)))
            return _redirect(start_response, f"/login?flash={str(exc).replace(' ', '+')}")
        except AuthorizationError as exc:
            user = _safe_user(auth, environ.get("HTTP_COOKIE"))
            return _html(
                start_response,
                403,
                render_page("Forbidden", f"<p>{str(exc)}</p>", user=user),
            )
        except DomainError as exc:
            user = _safe_user(auth, environ.get("HTTP_COOKIE"))
            return _html(
                start_response,
                422,
                render_page("Request Error", f"<p>{str(exc)}</p>", user=user, flash=str(exc)),
            )

    return app


def _json(start_response, status_code: int, payload: object):
    body = json.dumps(payload).encode("utf-8")
    start_response(
        f"{status_code} {_reason_phrase(status_code)}",
        [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def _html(start_response, status_code: int, html: str):
    body = html.encode("utf-8")
    start_response(
        f"{status_code} {_reason_phrase(status_code)}",
        [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def _redirect(start_response, location: str, headers: list[tuple[str, str]] | None = None):
    response_headers = [("Location", location), ("Content-Length", "0")]
    if headers:
        response_headers.extend(headers)
    start_response("303 See Other", response_headers)
    return [b""]


def _first(form: dict[str, list[str]], key: str, default: str = "") -> str:
    values = form.get(key)
    return values[0] if values else default


def _session_cookie(session_id: str) -> str:
    jar = cookies.SimpleCookie()
    jar["cars_session"] = session_id
    jar["cars_session"]["path"] = "/"
    jar["cars_session"]["httponly"] = True
    return jar.output(header="").strip()


def _expired_session_cookie() -> str:
    jar = cookies.SimpleCookie()
    jar["cars_session"] = ""
    jar["cars_session"]["path"] = "/"
    jar["cars_session"]["max-age"] = 0
    return jar.output(header="").strip()


def _session_id(environ) -> str | None:
    return SessionAuth.extract_session_id(environ.get("HTTP_COOKIE"))


def _safe_user(auth: SessionAuth, cookie_header: str | None):
    try:
        return auth.authenticate_request(cookie_header)
    except AuthenticationError:
        return None


def _reason_phrase(status_code: int) -> str:
    return {
        200: "OK",
        201: "Created",
        303: "See Other",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        422: "Unprocessable Entity",
    }[status_code]
