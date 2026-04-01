## What changed

I corrected the VIP discount calculation so it applies only to taxable items and left free shipping eligibility based on the pre-discount subtotal.

## Why

The previous implementation discounted non-taxable items and accidentally changed the shipping threshold behavior for VIP orders that landed exactly on the free-shipping boundary.

## Assumptions

- Shipping should still be waived when subtotal is exactly the threshold.
- The pricing service should keep its current public return shape.

## Risks

- If another service depends on the old discount behavior for non-taxable items, those callers may need coordinated updates.
- Floating-point arithmetic is still used here, so a future money type would be safer if the module grows.

## Test plan

- Ran acceptance tests covering the discount and shipping rules.
- Ran regression tests covering standard customers, small orders, and cent rounding.
