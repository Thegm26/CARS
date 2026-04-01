# CARS

This repo is becoming a small full-stack Python app first, and a CARS benchmark repo second.

The product in the repo is a `Returns and Claims` console for an ecommerce team. Customers can view their orders and submit return requests. Support staff and managers can review those requests, approve or reject them, and inspect the audit trail for each action.

The benchmark idea behind the repo is still `CARS`:

- `Correctness`
- `Alignment`
- `Reviewability`
- `Safety`

The long-term goal is to let this app generate realistic bugs, features, and maintenance tickets, and then evaluate agent deliveries against those tasks with CARS.

## CI

GitHub Actions now runs two separate pull request workflows:

- `CARS Correctness`
- `CARS ARS Gate`

`CARS Correctness` runs the returns-app test suite and owns the `C` in CARS.

`CARS ARS Gate` is intentionally not responsible for correctness. It checks only:

- `Alignment`
- `Reviewability`
- `Safety`

That means PRs now have a clean split:

- standard automated tests for `C`
- PR metadata and diff validation for `A`, `R`, and `S`

### PR Metadata Convention

Every PR is expected to include:

- `.cars/manifest.json`
- `.cars/delivery.md`

`.cars/manifest.json` must declare:

- `task_id`
- `touched_files`
- `acceptance_mapping`

`.cars/delivery.md` must include the review sections required by the referenced task.

The ARS gate then:

- compares the PR diff to the task's allowed scope
- checks that all acceptance criteria are mapped
- checks that the delivery notes are reviewable
- scans changed Python files for banned unsafe calls

## What The App Does

The current app models a simple returns workflow:

- customers can sign in and view their own orders
- customers can open a return request for eligible orders
- return requests contain selected items and notes
- managers can review pending requests
- approvals and rejections are recorded in an audit trail

This is intentionally small, but it is large enough to create meaningful future tickets around:

- authorization
- state transitions
- refund logic
- UI behavior
- auditability

## Who Uses It

There are three roles in the app:

- `customer`
  Customers can see their own orders and their own return requests.
- `support_agent`
  Support agents represent the support team. They have broader visibility into operational data.
- `support_manager`
  Managers can review pending requests and make approval decisions.

## Current Product Surfaces

The app currently includes:

- login page
- dashboard
- order detail page
- return request creation flow
- return request detail page
- manager review queue
- audit trail display

The implementation is deliberately simple:

- Python
- WSGI app
- SQLite database
- server-rendered HTML
- no frontend build step

## Quick Start

From the repo root:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/cars-returns --init-db
./.venv/bin/cars-returns
```

Then open:

```text
http://127.0.0.1:8000
```

## Demo Accounts

- `customer@example.com` / `customer123`
- `agent@example.com` / `agent123`
- `manager@example.com` / `manager123`

## Runtime Details

- the default SQLite database is `var/cars_returns.db`
- you can override the database path with `--db-path`
- you can also override it with `CARS_RETURNS_DB_PATH`

Example:

```bash
./.venv/bin/cars-returns --init-db --db-path /tmp/cars_returns.db
./.venv/bin/cars-returns --db-path /tmp/cars_returns.db
```

## Tests

Targeted returns-app tests:

```bash
./.venv/bin/python -m unittest tests.acceptance.test_returns_workflow tests.regression.test_returns_regressions tests.regression.test_returns_http
```

The repo also still contains the original pricing-based CARS demo. That older demo intentionally keeps a broken baseline in `src/cars_store/`, so full test discovery across the entire repository is not expected to pass unless you are specifically working on that demo flow.

## Repository Layout

- `src/cars_returns/`
  Product code for the returns app.
- `tests/acceptance/`
  Workflow-oriented tests.
- `tests/regression/`
  Behavioral and HTTP regression tests.
- `tasks/returns-*/`
  Early task definitions for future benchmark use.
- `.cars/`
  Per-PR metadata used by the CARS ARS gate.
- `src/cars_store/`
  Original small pricing demo used to explain the first CARS concept.
- `tasks/cart-discount/`
  Original example benchmark task and submissions.
- `cars_eval/`
  Initial evaluator used by the original benchmark demo.
- `docs/app-plan.md`
  Planning notes for growing the app into a stronger benchmark base.
- `docs/metric.md`
  Notes on why CARS is framed as gated evaluation instead of a weighted average.

## Why The Benchmark Files Are Still Here

This repo started as a narrow benchmark demo before it started moving toward a real app.

The old benchmark artifacts are still useful because they show the core CARS argument:

- a task can pass executable tests
- and still fail to be team-usable

The difference now is that the repo is shifting toward a stronger foundation:

1. build a real app
2. define realistic tickets against that app
3. evaluate agent deliveries with CARS

## Current Direction

The current priority is product development, not benchmark polish.

The app needs to become a coherent small system first. After that, the next logical step is to create real tickets for:

- feature work
- bug fixes
- authorization issues
- workflow changes
- UI regressions

Then CARS can be applied to those tickets in a way that is much more credible than a toy example.
