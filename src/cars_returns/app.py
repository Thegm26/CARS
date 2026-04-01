from __future__ import annotations

import json
from wsgiref.util import setup_testing_defaults

from cars_returns.auth import AuthenticationError, AuthorizationError
from cars_returns.models import ReturnRequestItem
from cars_returns.seed import build_seed_app_context
from cars_returns.service import DomainError


def create_app():
    auth, service = build_seed_app_context()

    def app(environ, start_response):
        setup_testing_defaults(environ)
        method = environ["REQUEST_METHOD"]
        path = environ["PATH_INFO"]
        body_bytes = environ["wsgi.input"].read(int(environ.get("CONTENT_LENGTH") or "0"))
        body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}

        try:
            user = auth.authenticate(environ.get("HTTP_AUTHORIZATION"))
            if path == "/health" and method == "GET":
                return _json(start_response, 200, {"status": "ok"})
            if path == "/orders" and method == "GET":
                orders = service.list_orders_for_user(user)
                payload = [
                    {
                        "id": order.id,
                        "customer_id": order.customer_id,
                        "shipping_paid": order.shipping_paid,
                    }
                    for order in orders
                ]
                return _json(start_response, 200, payload)
            if path.startswith("/orders/") and method == "GET":
                order_id = path.split("/")[2]
                order = service.get_order_for_user(user, order_id)
                return _html(
                    start_response,
                    200,
                    f"<h1>Order {order.id}</h1><p>Customer: {order.customer_id}</p>",
                )
            if path == "/return-requests" and method == "POST":
                items = [
                    ReturnRequestItem(sku=item["sku"], quantity=item["quantity"])
                    for item in body.get("items", [])
                ]
                request = service.create_return_request(
                    user,
                    body["order_id"],
                    items,
                    notes=body.get("notes", ""),
                )
                return _json(
                    start_response,
                    201,
                    {
                        "id": request.id,
                        "status": request.status,
                        "refund_total": service.calculate_refund_total(request.id),
                    },
                )
            if path.startswith("/return-requests/") and path.endswith("/approve") and method == "POST":
                request_id = path.split("/")[2]
                request = service.approve_return_request(user, request_id)
                return _json(start_response, 200, {"id": request.id, "status": request.status})
            if path.startswith("/return-requests/") and path.endswith("/reject") and method == "POST":
                request_id = path.split("/")[2]
                request = service.reject_return_request(user, request_id)
                return _json(start_response, 200, {"id": request.id, "status": request.status})
            if path.startswith("/return-requests/") and path.endswith("/audit") and method == "GET":
                request_id = path.split("/")[2]
                events = service.list_audit_events(user, request_id)
                rows = "".join(
                    f"<li>{event.action} by {event.actor_id} at {event.created_at.isoformat()}</li>"
                    for event in events
                )
                return _html(start_response, 200, f"<h1>Audit trail</h1><ul>{rows}</ul>")
            return _json(start_response, 404, {"error": "not found"})
        except AuthenticationError as exc:
            return _json(start_response, 401, {"error": str(exc)})
        except AuthorizationError as exc:
            return _json(start_response, 403, {"error": str(exc)})
        except DomainError as exc:
            return _json(start_response, 422, {"error": str(exc)})

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
    body = f"<!doctype html><html><body>{html}</body></html>".encode("utf-8")
    start_response(
        f"{status_code} {_reason_phrase(status_code)}",
        [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def _reason_phrase(status_code: int) -> str:
    return {
        200: "OK",
        201: "Created",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        422: "Unprocessable Entity",
    }[status_code]

