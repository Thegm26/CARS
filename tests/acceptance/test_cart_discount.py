from __future__ import annotations

import unittest

from tests.helpers import get_pricing_module


class CartDiscountAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        pricing = get_pricing_module()
        self.CartItem = pricing.CartItem
        self.calculate_total = pricing.calculate_total

    def test_vip_discount_applies_only_to_taxable_items(self) -> None:
        items = [
            self.CartItem("book", 30.00, quantity=1, taxable=False),
            self.CartItem("headphones", 50.00, quantity=1, taxable=True),
        ]

        result = self.calculate_total(items, customer_tier="vip")

        self.assertEqual(result["discount"], 5.00)
        self.assertEqual(result["total"], 82.50)

    def test_free_shipping_threshold_uses_pre_discount_subtotal(self) -> None:
        items = [
            self.CartItem("monitor", 80.00, quantity=1, taxable=True),
            self.CartItem("cable", 20.00, quantity=1, taxable=True),
        ]

        result = self.calculate_total(items, customer_tier="vip")

        self.assertEqual(result["subtotal"], 100.00)
        self.assertEqual(result["shipping"], 0.00)
        self.assertEqual(result["total"], 90.00)
