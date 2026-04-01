## What changed

Added a manager-only bulk approval endpoint for return requests. The service can now approve multiple pending requests in one call, and the app exposes that behavior through a new `/returns/bulk-approve` route. I also added regression coverage for successful manager bulk approval, unauthorized access, and mixed valid/invalid request ids.

## Why

Issue #6 requires managers to bulk approve eligible return requests without giving that capability to unauthorized users and without silently approving invalid items. The implementation keeps the work limited to the route, service logic, and regression coverage named in the issue scope.

## Assumptions

- Bulk approval is intended for managers only, not general support agents.
- Invalid request ids should be reported in the response while valid pending requests in the same batch are still approved.
- The bulk endpoint can return JSON even though the rest of the app is largely server-rendered HTML.

## Risks

- Mixed-result bulk operations are more complex to reason about than single-request approval.
- Future UI work will still need to expose the bulk endpoint through a manager-facing screen.
- Re-approving previously processed requests remains dependent on the request status model staying simple.

## Test plan

- Ran `python -m unittest tests.regression.test_returns_http`
- Ran `python scripts/run_pr_ars_ci.py`
