from __future__ import annotations

from copy import deepcopy
import json
import sqlite3
from datetime import datetime

from cars_returns.models import (
    AuditEvent,
    Order,
    OrderItem,
    ReturnRequest,
    ReturnRequestItem,
    User,
)


class InMemoryRepository:
    def __init__(
        self,
        orders: list[Order],
        users: list[User] | None = None,
        return_requests: list[ReturnRequest] | None = None,
        audit_events: list[AuditEvent] | None = None,
    ) -> None:
        self.users = {user.id: deepcopy(user) for user in (users or [])}
        self.orders = {order.id: deepcopy(order) for order in orders}
        self.return_requests = {
            request.id: deepcopy(request) for request in (return_requests or [])
        }
        self.audit_events = list(deepcopy(audit_events or []))

    def get_user_by_id(self, user_id: str) -> User | None:
        user = self.users.get(user_id)
        return deepcopy(user) if user is not None else None

    def get_user_by_email(self, email: str) -> User | None:
        for user in self.users.values():
            if user.email == email:
                return deepcopy(user)
        return None

    def get_order(self, order_id: str) -> Order | None:
        order = self.orders.get(order_id)
        return deepcopy(order) if order is not None else None

    def list_orders(self) -> list[Order]:
        return [deepcopy(order) for order in self.orders.values()]

    def get_return_request(self, request_id: str) -> ReturnRequest | None:
        request = self.return_requests.get(request_id)
        return deepcopy(request) if request is not None else None

    def list_return_requests(self) -> list[ReturnRequest]:
        return [deepcopy(request) for request in self.return_requests.values()]

    def list_return_requests_for_customer(self, customer_id: str) -> list[ReturnRequest]:
        return [
            deepcopy(request)
            for request in self.return_requests.values()
            if request.customer_id == customer_id
        ]

    def list_pending_return_requests(self) -> list[ReturnRequest]:
        return [
            deepcopy(request)
            for request in self.return_requests.values()
            if request.status == "pending"
        ]

    def save_return_request(self, request: ReturnRequest) -> ReturnRequest:
        self.return_requests[request.id] = deepcopy(request)
        return deepcopy(request)

    def add_audit_event(self, event: AuditEvent) -> AuditEvent:
        self.audit_events.append(deepcopy(event))
        return deepcopy(event)

    def list_audit_events_for_request(self, request_id: str) -> list[AuditEvent]:
        return [
            deepcopy(event)
            for event in self.audit_events
            if event.request_id == request_id
        ]


class SQLiteRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def get_user_by_id(self, user_id: str) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, email, name, role, password_hash FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return self._user_from_row(row)

    def get_user_by_email(self, email: str) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, email, name, role, password_hash FROM users WHERE email = ?",
                (email,),
            ).fetchone()
        return self._user_from_row(row)

    def get_order(self, order_id: str) -> Order | None:
        with self._connect() as conn:
            order_row = conn.execute(
                """
                SELECT id, customer_id, created_at, delivered_at, shipping_paid
                FROM orders
                WHERE id = ?
                """,
                (order_id,),
            ).fetchone()
            if order_row is None:
                return None
            item_rows = conn.execute(
                """
                SELECT sku, name, unit_price, quantity
                FROM order_items
                WHERE order_id = ?
                ORDER BY id
                """,
                (order_id,),
            ).fetchall()
        return self._order_from_rows(order_row, item_rows)

    def list_orders(self) -> list[Order]:
        with self._connect() as conn:
            order_rows = conn.execute(
                """
                SELECT id, customer_id, created_at, delivered_at, shipping_paid
                FROM orders
                ORDER BY created_at DESC
                """
            ).fetchall()
            item_rows = conn.execute(
                """
                SELECT order_id, sku, name, unit_price, quantity
                FROM order_items
                ORDER BY id
                """
            ).fetchall()
        items_by_order: dict[str, list[sqlite3.Row]] = {}
        for row in item_rows:
            items_by_order.setdefault(row["order_id"], []).append(row)
        return [
            self._order_from_rows(order_row, items_by_order.get(order_row["id"], []))
            for order_row in order_rows
        ]

    def get_return_request(self, request_id: str) -> ReturnRequest | None:
        with self._connect() as conn:
            request_row = conn.execute(
                """
                SELECT id, order_id, customer_id, status, created_by, created_at, notes,
                       decision_by, decision_at
                FROM return_requests
                WHERE id = ?
                """,
                (request_id,),
            ).fetchone()
            if request_row is None:
                return None
            item_rows = conn.execute(
                """
                SELECT sku, quantity
                FROM return_request_items
                WHERE request_id = ?
                ORDER BY id
                """,
                (request_id,),
            ).fetchall()
        return self._request_from_rows(request_row, item_rows)

    def list_return_requests(self) -> list[ReturnRequest]:
        with self._connect() as conn:
            request_rows = conn.execute(
                """
                SELECT id, order_id, customer_id, status, created_by, created_at, notes,
                       decision_by, decision_at
                FROM return_requests
                ORDER BY created_at DESC
                """
            ).fetchall()
            item_rows = conn.execute(
                """
                SELECT request_id, sku, quantity
                FROM return_request_items
                ORDER BY id
                """
            ).fetchall()
        items_by_request: dict[str, list[sqlite3.Row]] = {}
        for row in item_rows:
            items_by_request.setdefault(row["request_id"], []).append(row)
        return [
            self._request_from_rows(request_row, items_by_request.get(request_row["id"], []))
            for request_row in request_rows
        ]

    def list_return_requests_for_customer(self, customer_id: str) -> list[ReturnRequest]:
        return [
            request
            for request in self.list_return_requests()
            if request.customer_id == customer_id
        ]

    def list_pending_return_requests(self) -> list[ReturnRequest]:
        return [
            request
            for request in self.list_return_requests()
            if request.status == "pending"
        ]

    def save_return_request(self, request: ReturnRequest) -> ReturnRequest:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO return_requests (
                    id, order_id, customer_id, status, created_by, created_at, notes, decision_by, decision_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    notes = excluded.notes,
                    decision_by = excluded.decision_by,
                    decision_at = excluded.decision_at
                """,
                (
                    request.id,
                    request.order_id,
                    request.customer_id,
                    request.status,
                    request.created_by,
                    request.created_at.isoformat(),
                    request.notes,
                    request.decision_by,
                    request.decision_at.isoformat() if request.decision_at else None,
                ),
            )
            conn.execute(
                "DELETE FROM return_request_items WHERE request_id = ?",
                (request.id,),
            )
            conn.executemany(
                """
                INSERT INTO return_request_items (request_id, sku, quantity)
                VALUES (?, ?, ?)
                """,
                [
                    (request.id, item.sku, item.quantity)
                    for item in request.requested_items
                ],
            )
            conn.commit()
        return request

    def add_audit_event(self, event: AuditEvent) -> AuditEvent:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (id, request_id, actor_id, action, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.request_id,
                    event.actor_id,
                    event.action,
                    event.created_at.isoformat(),
                    json.dumps(event.metadata, sort_keys=True),
                ),
            )
            conn.commit()
        return event

    def list_audit_events_for_request(self, request_id: str) -> list[AuditEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, request_id, actor_id, action, created_at, metadata_json
                FROM audit_events
                WHERE request_id = ?
                ORDER BY created_at ASC
                """,
                (request_id,),
            ).fetchall()
        return [
            AuditEvent(
                id=row["id"],
                request_id=row["request_id"],
                actor_id=row["actor_id"],
                action=row["action"],
                created_at=datetime.fromisoformat(row["created_at"]),
                metadata=json.loads(row["metadata_json"] or "{}"),
            )
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _user_from_row(row: sqlite3.Row | None) -> User | None:
        if row is None:
            return None
        return User(
            id=row["id"],
            email=row["email"],
            name=row["name"],
            role=row["role"],
            password_hash=row["password_hash"],
        )

    @staticmethod
    def _order_from_rows(order_row: sqlite3.Row, item_rows: list[sqlite3.Row]) -> Order:
        return Order(
            id=order_row["id"],
            customer_id=order_row["customer_id"],
            created_at=datetime.fromisoformat(order_row["created_at"]),
            delivered_at=(
                datetime.fromisoformat(order_row["delivered_at"])
                if order_row["delivered_at"]
                else None
            ),
            items=[
                OrderItem(
                    sku=row["sku"],
                    name=row["name"],
                    unit_price=row["unit_price"],
                    quantity=row["quantity"],
                )
                for row in item_rows
            ],
            shipping_paid=order_row["shipping_paid"],
        )

    @staticmethod
    def _request_from_rows(
        request_row: sqlite3.Row,
        item_rows: list[sqlite3.Row],
    ) -> ReturnRequest:
        return ReturnRequest(
            id=request_row["id"],
            order_id=request_row["order_id"],
            customer_id=request_row["customer_id"],
            status=request_row["status"],
            created_by=request_row["created_by"],
            created_at=datetime.fromisoformat(request_row["created_at"]),
            requested_items=[
                ReturnRequestItem(sku=row["sku"], quantity=row["quantity"])
                for row in item_rows
            ],
            notes=request_row["notes"] or "",
            decision_by=request_row["decision_by"],
            decision_at=(
                datetime.fromisoformat(request_row["decision_at"])
                if request_row["decision_at"]
                else None
            ),
        )
