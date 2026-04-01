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

    # Baseline bug:
    # 1. VIP discount is applied to the full subtotal instead of taxable items only.
    # 2. Shipping is decided from the discounted subtotal, which changes legacy behavior.
    # 3. Rounding happens at multiple points instead of once at the end.
    discount = round(subtotal * 0.10, 2) if customer_tier == "vip" else 0.0
    shipping = 0.0 if round(subtotal - discount, 2) >= free_shipping_threshold else shipping_fee
    total = round(round(subtotal - discount, 2) + shipping, 2)

    return {
        "subtotal": round(subtotal, 2),
        "taxable_subtotal": round(taxable_subtotal, 2),
        "discount": round(discount, 2),
        "shipping": round(shipping, 2),
        "total": round(total, 2),
    }
