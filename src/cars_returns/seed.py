from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cars_returns.auth import TokenAuth
from cars_returns.models import Order, OrderItem, ReturnRequest, ReturnRequestItem, User
from cars_returns.repository import InMemoryRepository
from cars_returns.service import ReturnsService


def build_seed_users() -> dict[str, User]:
    return {
        "customer-token": User(id="cust_1", email="customer@example.com", role="customer"),
        "agent-token": User(id="agent_1", email="agent@example.com", role="support_agent"),
        "manager-token": User(
            id="manager_1",
            email="manager@example.com",
            role="support_manager",
        ),
    }


def build_seed_repository() -> InMemoryRepository:
    now = datetime.now(UTC)
    orders = [
        Order(
            id="ord_100",
            customer_id="cust_1",
            created_at=now - timedelta(days=12),
            delivered_at=now - timedelta(days=7),
            items=[
                OrderItem("sku_keyboard", "Keyboard", 89.00, 1),
                OrderItem("sku_cable", "Cable", 12.50, 2),
            ],
            shipping_paid=9.99,
        ),
        Order(
            id="ord_200",
            customer_id="cust_2",
            created_at=now - timedelta(days=40),
            delivered_at=now - timedelta(days=35),
            items=[
                OrderItem("sku_mouse", "Mouse", 35.00, 1),
            ],
            shipping_paid=7.50,
        ),
    ]
    requests = [
        ReturnRequest(
            id="rr_900",
            order_id="ord_100",
            customer_id="cust_1",
            status="pending",
            created_by="cust_1",
            created_at=now - timedelta(days=1),
            requested_items=[ReturnRequestItem("sku_keyboard", 1)],
            notes="Key chatter on the A key",
        )
    ]
    return InMemoryRepository(orders, requests)


def build_seed_app_context() -> tuple[TokenAuth, ReturnsService]:
    users = build_seed_users()
    auth = TokenAuth(users)
    service = ReturnsService(build_seed_repository())
    return auth, service

