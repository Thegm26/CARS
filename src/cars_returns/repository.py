from __future__ import annotations

from copy import deepcopy

from cars_returns.models import AuditEvent, Order, ReturnRequest


class InMemoryRepository:
    def __init__(
        self,
        orders: list[Order],
        return_requests: list[ReturnRequest] | None = None,
        audit_events: list[AuditEvent] | None = None,
    ) -> None:
        self.orders = {order.id: deepcopy(order) for order in orders}
        self.return_requests = {
            request.id: deepcopy(request) for request in (return_requests or [])
        }
        self.audit_events = list(deepcopy(audit_events or []))

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

