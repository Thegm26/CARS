# Why CARS Uses Gates Instead of a Single Average

The primary metric in this repo is:

`Team-Usable Delivery Rate = deliveries that pass Correctness, Alignment, Reviewability, and Safety / total deliveries`

This is intentionally a gated metric, not a weighted average.

## Argument

Software delivery inside a team is a coordination problem, not just an output problem.

A patch is not valuable to a scrum team simply because it passes tests. It must also:

- implement the intended behavior
- be understandable by another engineer
- avoid risky implementation shortcuts

If any one of those conditions fails, the delivery is not genuinely merge-ready.

That is why CARS treats each dimension as a gate:

- a correct but unsafe patch should fail
- a correct but unreviewable patch should fail
- a readable but misaligned patch should fail

## Why not a weighted score

Weighted averages hide failure modes that teams care about.

Example:

- `Correctness = 1.0`
- `Alignment = 1.0`
- `Reviewability = 0.2`
- `Safety = 0.0`

A weighted average may still look acceptable. In practice, that patch should not be merged.

## What CARS reports

The evaluator reports:

- `raw_resolve_rate`
- `team_usable_delivery_rate`
- per-submission gate results
- a `rework_proxy`

This separation is deliberate:

- `raw_resolve_rate` tells you whether the agent can satisfy the task harness
- `team_usable_delivery_rate` tells you whether the team can realistically ship the result

## Research position encoded here

The repo takes the position that code-agent evaluation for teams should measure:

- executable correctness
- intent alignment
- explanation quality and reviewability
- operational safety

That is the minimum needed to reduce the understanding gap between developers and shipped code.
