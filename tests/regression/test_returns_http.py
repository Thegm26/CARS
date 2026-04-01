from __future__ import annotations

from io import BytesIO
from tempfile import TemporaryDirectory
from urllib.parse import urlencode
import unittest

from cars_returns.app import create_app


class ReturnsHttpRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.app = create_app(db_path=f"{self.temp_dir.name}/app.db", seed_demo=True)

    def test_customer_dashboard_only_shows_owned_orders(self) -> None:
        cookie = self.login("customer@example.com", "customer123")

        status, _, body = self.call_app(
            "GET",
            "/app",
            cookie=cookie,
        )

        self.assertEqual(status, "200 OK")
        self.assertIn("ord_100", body)
        self.assertIn("Returns Dashboard", body)
        self.assertNotIn("ord_200", body)

    def test_missing_session_redirects_to_login(self) -> None:
        status, headers, _ = self.call_app("GET", "/app")

        self.assertEqual(status, "303 See Other")
        self.assertIn(("Location", "/login?flash=login+required"), headers)

    def test_manager_can_open_review_queue(self) -> None:
        cookie = self.login("manager@example.com", "manager123")

        status, headers, body = self.call_app(
            "GET",
            "/manager/queue",
            cookie=cookie,
        )

        self.assertEqual(status, "200 OK")
        self.assertIn(("Content-Type", "text/html; charset=utf-8"), headers)
        self.assertIn("Pending Review Queue", body)
        self.assertIn("rr_900", body)

    def test_customer_can_submit_return_request_from_order_page(self) -> None:
        cookie = self.login("customer@example.com", "customer123")

        status, headers, _ = self.call_app(
            "POST",
            "/orders/ord_100/returns",
            cookie=cookie,
            form_body={
                "qty_sku_keyboard": "1",
                "qty_sku_cable": "0",
                "notes": "Keys keep repeating",
            },
        )

        self.assertEqual(status, "303 See Other")
        location = dict(headers)["Location"]
        self.assertTrue(location.startswith("/returns/rr_"))

        detail_status, _, detail_body = self.call_app("GET", location, cookie=cookie)
        self.assertEqual(detail_status, "200 OK")
        self.assertIn("Keys keep repeating", detail_body)
        self.assertIn("Refund total: $89.00", detail_body)

    def call_app(
        self,
        method: str,
        path: str,
        *,
        cookie: str | None = None,
        form_body: dict[str, str] | None = None,
    ) -> tuple[str, list[tuple[str, str]], str]:
        encoded_body = urlencode(form_body or {})
        body = encoded_body.encode("utf-8")
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "CONTENT_LENGTH": str(len(body)),
            "CONTENT_TYPE": "application/x-www-form-urlencoded",
            "wsgi.input": BytesIO(body),
        }
        if cookie is not None:
            environ["HTTP_COOKIE"] = cookie

        captured: dict[str, object] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            captured["status"] = status
            captured["headers"] = headers

        response_body = b"".join(self.app(environ, start_response)).decode("utf-8")
        return captured["status"], captured["headers"], response_body

    def login(self, email: str, password: str) -> str:
        status, headers, _ = self.call_app(
            "POST",
            "/login",
            form_body={"email": email, "password": password},
        )
        self.assertEqual(status, "303 See Other")
        return dict(headers)["Set-Cookie"]
