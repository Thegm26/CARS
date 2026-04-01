from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CartItem:
    sku: str
    unit_price: float
    quantity: int = 1
    taxable: bool = True


def _round_money(amount: float) -> float:
    return round(amount + 1e-9, 2)


def calculate_total(
    items: list[CartItem],
    customer_tier: str,
    shipping_fee: float = 7.50,
    free_shipping_threshold: float = 100.00,
) -> dict[str, float]:
    subtotal = sum(item.unit_price * item.quantity for item in items)
    taxable_subtotal = sum(
        item.unit_price * item.quantity for item in items if item.taxable
    )

    discount = taxable_subtotal * 0.10 if customer_tier == "vip" else 0.0
    shipping = 0.0 if subtotal >= free_shipping_threshold else shipping_fee
    total = max(subtotal - discount + shipping, 0.0)

    return {
        "subtotal": _round_money(subtotal),
        "taxable_subtotal": _round_money(taxable_subtotal),
        "discount": _round_money(discount),
        "shipping": _round_money(shipping),
        "total": _round_money(total),
    }
