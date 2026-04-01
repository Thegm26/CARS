from __future__ import annotations

import unittest

from tests.helpers import get_pricing_module


class PricingRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        pricing = get_pricing_module()
        self.CartItem = pricing.CartItem
        self.calculate_total = pricing.calculate_total

    def test_regular_customers_keep_existing_shipping_behavior(self) -> None:
        items = [self.CartItem("keyboard", 40.00, quantity=2, taxable=True)]

        result = self.calculate_total(items, customer_tier="standard")

        self.assertEqual(result["discount"], 0.00)
        self.assertEqual(result["shipping"], 7.50)
        self.assertEqual(result["total"], 87.50)

    def test_totals_do_not_go_negative_for_small_orders(self) -> None:
        items = [self.CartItem("sticker", 0.99, quantity=1, taxable=True)]

        result = self.calculate_total(items, customer_tier="vip")

        self.assertGreaterEqual(result["total"], 0.00)
        self.assertEqual(result["shipping"], 7.50)

    def test_rounding_occurs_to_cents(self) -> None:
        items = [self.CartItem("cable", 19.995, quantity=1, taxable=True)]

        result = self.calculate_total(items, customer_tier="standard")

        self.assertEqual(result["subtotal"], 20.00)
        self.assertEqual(result["total"], 27.50)
