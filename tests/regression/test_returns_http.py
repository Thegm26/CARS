from __future__ import annotations

from io import BytesIO
import json
import unittest

from cars_returns.app import create_app


class ReturnsHttpRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()

    def test_customer_only_sees_owned_orders_in_list(self) -> None:
        status, headers, body = self.call_app(
            "GET",
            "/orders",
            token="customer-token",
        )

        payload = json.loads(body)
        self.assertEqual(status, "200 OK")
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["id"], "ord_100")

    def test_missing_auth_header_returns_401(self) -> None:
        status, _, body = self.call_app("GET", "/orders")

        self.assertEqual(status, "401 Unauthorized")
        self.assertIn("missing authorization header", body)

    def test_audit_page_renders_html(self) -> None:
        status, headers, body = self.call_app(
            "GET",
            "/return-requests/rr_900/audit",
            token="manager-token",
        )

        self.assertEqual(status, "200 OK")
        self.assertIn(("Content-Type", "text/html; charset=utf-8"), headers)
        self.assertIn("Audit trail", body)

    def call_app(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json_body: dict[str, object] | None = None,
    ) -> tuple[str, list[tuple[str, str]], str]:
        body = json.dumps(json_body).encode("utf-8") if json_body is not None else b""
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": BytesIO(body),
        }
        if token is not None:
            environ["HTTP_AUTHORIZATION"] = f"Bearer {token}"

        captured: dict[str, object] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            captured["status"] = status
            captured["headers"] = headers

        response_body = b"".join(self.app(environ, start_response)).decode("utf-8")
        return captured["status"], captured["headers"], response_body

