# CARS

CARS stands for `Correctness, Alignment, Reviewability, and Safety`.

This repo is a small demonstration of a coding-agent evaluation model for scrum teams. It argues that `resolved_tasks / total_tasks` is not enough. A team needs code that is:

- correct
- aligned with ticket intent
- reviewable by another engineer
- safe to ship

The primary metric in this repo is:

`Team-Usable Delivery Rate = deliveries that pass all CARS gates / total deliveries`

## Why this repo exists

Most coding-agent benchmarks reward task completion. Real teams merge code only when a change is technically correct and understandable. CARS turns that into an explicit evaluation rule.

In this demo:

- the task is a pricing fix in a small store service
- there are acceptance tests and regression tests
- there are two agent submissions: `good` and `bad`
- both submissions pass the executable tests
- only one passes the full CARS evaluation

That contrast is the point of the repo.

## Repository layout

- `src/cars_store/`: baseline application code with the pricing bug
- `tests/acceptance/`: tests tied to the user-facing ticket
- `tests/regression/`: tests protecting existing behavior
- `tasks/cart-discount/`: task spec plus example agent submissions
- `cars_eval/`: the CARS evaluator

## Evaluation model

Each delivery is scored on four gates:

1. `Correctness`
   The candidate must pass acceptance and regression tests.

2. `Alignment`
   The delivery must map its implementation to the acceptance criteria and stay within the allowed scope for the ticket.

3. `Reviewability`
   Another engineer must be able to understand what changed, why, assumptions, risks, and how it was tested.

4. `Safety`
   The change must avoid banned unsafe patterns.

The evaluator also computes a `rework_proxy` so you can see whether the change is likely to create downstream review pain, but it is reported separately from the main gate.

The rationale for this gated design is documented in [docs/metric.md](/home/gm26/experimenting/CARS/docs/metric.md).

## Commands

Evaluate both example submissions:

```bash
python -m cars_eval --task cart-discount --all
```

Evaluate one submission:

```bash
python -m cars_eval --task cart-discount --submission good
python -m cars_eval --task cart-discount --submission bad
```

Run the tests for a specific candidate module directly:

```bash
PYTHONPATH=src CARS_PRICING_PATH=tasks/cart-discount/submissions/good/pricing.py python -m unittest discover -s tests -t .
```

## Expected demo outcome

- `good`: passes CARS
- `bad`: passes correctness, fails reviewability and safety

So the raw resolve rate is `100%`, but the team-usable delivery rate is `50%`.

That is the behavior this repo is designed to display.
