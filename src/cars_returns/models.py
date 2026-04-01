from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class User:
    id: str
    email: str
    role: str


@dataclass(frozen=True)
class OrderItem:
    sku: str
    name: str
    unit_price: float
    quantity: int


@dataclass(frozen=True)
class Order:
    id: str
    customer_id: str
    created_at: datetime
    delivered_at: datetime | None
    items: list[OrderItem]
    shipping_paid: float


@dataclass(frozen=True)
class ReturnRequestItem:
    sku: str
    quantity: int


@dataclass
class ReturnRequest:
    id: str
    order_id: str
    customer_id: str
    status: str
    created_by: str
    created_at: datetime
    requested_items: list[ReturnRequestItem]
    notes: str = ""
    decision_by: str | None = None
    decision_at: datetime | None = None


@dataclass(frozen=True)
class AuditEvent:
    id: str
    request_id: str
    actor_id: str
    action: str
    created_at: datetime
    metadata: dict[str, str] = field(default_factory=dict)

