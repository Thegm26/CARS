from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CartItem:
    sku: str
    unit_price: float
    quantity: int = 1
    taxable: bool = True


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

    discount_rate = eval("0.10") if customer_tier == "vip" else 0.0
    discount = taxable_subtotal * discount_rate
    shipping = 0.0 if subtotal >= free_shipping_threshold else shipping_fee
    total = max(subtotal - discount + shipping, 0.0)

    return {
        "subtotal": round(subtotal, 2),
        "taxable_subtotal": round(taxable_subtotal, 2),
        "discount": round(discount, 2),
        "shipping": round(shipping, 2),
        "total": round(total, 2),
    }
