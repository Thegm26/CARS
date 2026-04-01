from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from html import escape
from itertools import count

from cars_returns.auth import AuthorizationError, require_role
from cars_returns.models import AuditEvent, Order, ReturnRequest, ReturnRequestItem, User
from cars_returns.repository import InMemoryRepository


class DomainError(Exception):
    pass


REQUEST_SEQUENCE = count(1000)
AUDIT_SEQUENCE = count(5001)


class ReturnsService:
    def __init__(
        self,
        repository: InMemoryRepository,
        *,
        manager_approval_threshold: float = 75.00,
        return_window_days: int = 30,
    ) -> None:
        self.repository = repository
        self.manager_approval_threshold = manager_approval_threshold
        self.return_window_days = return_window_days

    def list_orders_for_user(self, user: User) -> list[Order]:
        orders = self.repository.list_orders()
        if user.role in {"support_agent", "support_manager"}:
            return orders
        return [order for order in orders if order.customer_id == user.id]

    def list_return_requests_for_user(self, user: User) -> list[ReturnRequest]:
        if user.role in {"support_agent", "support_manager"}:
            return self.repository.list_return_requests()
        return self.repository.list_return_requests_for_customer(user.id)

    def list_pending_requests_for_review(self, user: User) -> list[ReturnRequest]:
        require_role(user, {"support_manager"})
        return self.repository.list_pending_return_requests()

    def get_order_for_user(self, user: User, order_id: str) -> Order:
        order = self.repository.get_order(order_id)
        if order is None:
            raise DomainError("order not found")
        if user.role not in {"support_agent", "support_manager"} and order.customer_id != user.id:
            raise AuthorizationError("order is not visible to this user")
        return order

    def is_return_eligible(self, order: Order, *, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        if order.delivered_at is None:
            return False
        deadline = order.delivered_at + timedelta(days=self.return_window_days)
        return now <= deadline

    def create_return_request(
        self,
        user: User,
        order_id: str,
        items: list[ReturnRequestItem],
        notes: str = "",
    ) -> ReturnRequest:
        order = self.get_order_for_user(user, order_id)
        if not self.is_return_eligible(order):
            raise DomainError("order is outside the return window")
        allowed_quantities = {item.sku: item.quantity for item in order.items}
        if not items:
            raise DomainError("at least one item must be selected")
        for item in items:
            if item.sku not in allowed_quantities:
                raise DomainError(f"unknown sku: {item.sku}")
            if item.quantity <= 0 or item.quantity > allowed_quantities[item.sku]:
                raise DomainError(f"invalid quantity for sku: {item.sku}")

        request = ReturnRequest(
            id=f"rr_{next(REQUEST_SEQUENCE)}",
            order_id=order.id,
            customer_id=order.customer_id,
            status="pending",
            created_by=user.id,
            created_at=datetime.now(UTC),
            requested_items=items,
            notes=notes,
        )
        saved = self.repository.save_return_request(request)
        self._audit(saved.id, user.id, "return_request_created")
        return saved

    def calculate_refund_total(self, request_id: str) -> float:
        request = self._get_request(request_id)
        order = self._get_order(request.order_id)
        item_prices = {item.sku: item.unit_price for item in order.items}
        item_total = sum(
            item_prices[request_item.sku] * request_item.quantity
            for request_item in request.requested_items
        )
        return round(item_total, 2)

    def approve_return_request(self, user: User, request_id: str) -> ReturnRequest:
        request = self._get_request(request_id)
        require_role(user, {"support_agent", "support_manager"})
        if request.status == "rejected":
            raise DomainError("rejected requests cannot be approved")
        refund_total = self.calculate_refund_total(request_id)
        if refund_total > self.manager_approval_threshold and user.role != "support_manager":
            raise AuthorizationError("manager approval required above threshold")
        updated = replace(
            request,
            status="approved",
            decision_by=user.id,
            decision_at=datetime.now(UTC),
        )
        saved = self.repository.save_return_request(updated)
        self._audit(saved.id, user.id, "return_request_approved")
        return saved

    def bulk_approve_return_requests(
        self,
        user: User,
        request_ids: list[str],
    ) -> dict[str, list[str]]:
        require_role(user, {"support_agent", "support_manager"})
        approved_request_ids: list[str] = []
        for request_id in request_ids:
            request = self.repository.get_return_request(request_id)
            if request is None or request.status != "pending":
                continue
            approved = self.approve_return_request(user, request_id)
            approved_request_ids.append(approved.id)
        return {
            "approved_request_ids": approved_request_ids,
            "invalid_request_ids": [],
        }

    def reject_return_request(self, user: User, request_id: str) -> ReturnRequest:
        request = self._get_request(request_id)
        require_role(user, {"support_agent", "support_manager"})
        if request.status == "approved":
            raise DomainError("approved requests cannot be rejected")
        updated = replace(
            request,
            status="rejected",
            decision_by=user.id,
            decision_at=datetime.now(UTC),
        )
        saved = self.repository.save_return_request(updated)
        self._audit(saved.id, user.id, "return_request_rejected")
        return saved

    def list_audit_events(self, user: User, request_id: str) -> list[AuditEvent]:
        request = self._get_request(request_id)
        if user.role not in {"support_agent", "support_manager"} and request.customer_id != user.id:
            raise AuthorizationError("return request is not visible to this user")
        return self.repository.list_audit_events_for_request(request_id)

    def get_return_request_for_user(self, user: User, request_id: str) -> ReturnRequest:
        request = self._get_request(request_id)
        if user.role not in {"support_agent", "support_manager"} and request.customer_id != user.id:
            raise AuthorizationError("return request is not visible to this user")
        return request

    @staticmethod
    def sanitize_notes(notes: str) -> str:
        return escape(notes, quote=True)

    def _get_order(self, order_id: str) -> Order:
        order = self.repository.get_order(order_id)
        if order is None:
            raise DomainError("order not found")
        return order

    def _get_request(self, request_id: str) -> ReturnRequest:
        request = self.repository.get_return_request(request_id)
        if request is None:
            raise DomainError("return request not found")
        return request

    def _audit(self, request_id: str, actor_id: str, action: str) -> None:
        event = AuditEvent(
            id=f"ae_{next(AUDIT_SEQUENCE)}",
            request_id=request_id,
            actor_id=actor_id,
            action=action,
            created_at=datetime.now(UTC),
        )
        self.repository.add_audit_event(event)
