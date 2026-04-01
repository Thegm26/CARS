from __future__ import annotations

from datetime import UTC, datetime, timedelta
import unittest

from cars_returns.auth import AuthorizationError
from cars_returns.models import Order, OrderItem, ReturnRequest, ReturnRequestItem, User
from cars_returns.repository import InMemoryRepository
from cars_returns.service import DomainError, ReturnsService


class ReturnsRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        now = datetime.now(UTC)
        self.customer = User(
            id="cust_1",
            email="customer@example.com",
            name="Jamie Customer",
            role="customer",
        )
        self.agent = User(
            id="agent_1",
            email="agent@example.com",
            name="Alex Agent",
            role="support_agent",
        )
        self.manager = User(
            id="manager_1",
            email="manager@example.com",
            name="Riley Manager",
            role="support_manager",
        )
        orders = [
            Order(
                id="ord_100",
                customer_id="cust_1",
                created_at=now - timedelta(days=20),
                delivered_at=now - timedelta(days=5),
                items=[OrderItem("sku_keyboard", "Keyboard", 89.00, 1)],
                shipping_paid=9.99,
            ),
            Order(
                id="ord_200",
                customer_id="cust_2",
                created_at=now - timedelta(days=45),
                delivered_at=now - timedelta(days=40),
                items=[OrderItem("sku_mouse", "Mouse", 35.00, 1)],
                shipping_paid=7.50,
            ),
        ]
        return_requests = [
            ReturnRequest(
                id="rr_090",
                order_id="ord_100",
                customer_id="cust_1",
                status="pending",
                created_by="cust_1",
                created_at=now - timedelta(days=1),
                requested_items=[ReturnRequestItem("sku_keyboard", 1)],
            ),
            ReturnRequest(
                id="rr_100",
                order_id="ord_100",
                customer_id="cust_1",
                status="rejected",
                created_by="cust_1",
                created_at=now - timedelta(days=1),
                requested_items=[ReturnRequestItem("sku_keyboard", 1)],
            )
        ]
        self.service = ReturnsService(
            InMemoryRepository(orders, [self.customer, self.agent, self.manager], return_requests)
        )

    def test_support_agent_cannot_approve_high_value_return(self) -> None:
        with self.assertRaises(AuthorizationError):
            self.service.approve_return_request(self.agent, "rr_090")

    def test_rejected_request_cannot_transition_to_approved(self) -> None:
        with self.assertRaises(DomainError):
            self.service.approve_return_request(self.manager, "rr_100")

    def test_customers_cannot_view_other_customer_orders(self) -> None:
        with self.assertRaises(AuthorizationError):
            self.service.get_order_for_user(self.customer, "ord_200")

    def test_return_window_uses_delivery_date(self) -> None:
        order = self.service.get_order_for_user(self.agent, "ord_100")

        self.assertTrue(self.service.is_return_eligible(order))
