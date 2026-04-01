from __future__ import annotations

from datetime import UTC, datetime, timedelta
import unittest

from cars_returns.models import Order, OrderItem, ReturnRequestItem, User
from cars_returns.repository import InMemoryRepository
from cars_returns.service import ReturnsService


class ReturnsWorkflowAcceptanceTests(unittest.TestCase):
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
        order = Order(
            id="ord_100",
            customer_id="cust_1",
            created_at=now - timedelta(days=3),
            delivered_at=now - timedelta(days=2),
            items=[
                OrderItem("sku_keyboard", "Keyboard", 89.00, 1),
                OrderItem("sku_cable", "Cable", 12.50, 2),
            ],
            shipping_paid=9.99,
        )
        self.service = ReturnsService(InMemoryRepository([order], [self.customer, self.agent, self.manager]))

    def test_customer_can_create_a_return_request_for_owned_order(self) -> None:
        request = self.service.create_return_request(
            self.customer,
            "ord_100",
            [ReturnRequestItem("sku_keyboard", 1)],
            notes="Wrong switch feel",
        )

        self.assertEqual(request.status, "pending")
        self.assertEqual(request.customer_id, "cust_1")

    def test_refund_total_only_counts_requested_items(self) -> None:
        request = self.service.create_return_request(
            self.customer,
            "ord_100",
            [ReturnRequestItem("sku_cable", 1)],
        )

        self.assertEqual(self.service.calculate_refund_total(request.id), 12.50)

    def test_manager_can_approve_high_value_return(self) -> None:
        request = self.service.create_return_request(
            self.customer,
            "ord_100",
            [ReturnRequestItem("sku_keyboard", 1)],
        )

        approved = self.service.approve_return_request(self.manager, request.id)

        self.assertEqual(approved.status, "approved")
        self.assertEqual(approved.decision_by, "manager_1")
