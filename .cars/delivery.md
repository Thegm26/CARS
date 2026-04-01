## What changed

Split the original pull request benchmark workflow into two dedicated workflows. `CARS Correctness` now runs the returns test suite, and `CARS ARS Gate` now validates Alignment, Reviewability, and Safety from `.cars` metadata and the actual PR diff. I also replaced the old benchmark CI runner with a PR-oriented ARS runner and documented the convention in the README.

## Why

Correctness should be enforced by standard automated tests whether the PR comes from a human or an agent. The CARS-specific workflow should focus only on the non-correctness gates so the split is explicit and operationally clean.

## Assumptions

- Pull requests will include `.cars/manifest.json` and `.cars/delivery.md`.
- Task definitions will exist for process and CI work, not just product code changes.
- The returns test suite is the correctness baseline for the current application.

## Risks

- The ARS gate will fail any PR that does not have a task matching its real diff, which is strict by design.
- CI and process changes now need explicit task definitions, which adds workflow overhead.
- Future repos or broader test matrices may require expanding the correctness workflow beyond the current returns tests.

## Test plan

- Ran `python -m unittest tests.acceptance.test_returns_workflow tests.regression.test_returns_regressions tests.regression.test_returns_http`
- Ran `python scripts/run_pr_ars_ci.py`
