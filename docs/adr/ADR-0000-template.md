# ADR-NNNN: <decision title>

- **Status:** proposed | accepted | superseded by ADR-NNNN
- **Date:** YYYY-MM-DD
- **Doctrine:** axioms/patterns/frameworks applied or overridden (e.g. `AX-04`,
  `DD-11`, `PAT-11`, `DF-02`) — overrides must say why the default loses here
- **Owners:** <team/person accountable for the consequences>

## Context

The forces at play: the requirement, the actual (not imagined) scale, and the
evidence that makes this a decision rather than a doctrine default.

## Constraints

Hard limits the decision must respect: budget, compliance, latency, team size,
existing systems, deadlines.

## Quality attributes

The two or three attributes this decision optimizes (latency, integrity,
availability, cost, velocity…) — and what is deliberately sacrificed for them.

## Options considered

Each realistic option, including the doctrine default, with enough substance
that a future reader could re-run the comparison.

## Selected option

The choice, stated actively and specifically enough that a diff can be judged
against it.

## Benefits

What this buys, tied to the quality attributes above.

## Costs

What it spends: complexity, operational load, lock-in, latency, money.

## Failure modes

How the selected option breaks — under load, partial failure, misuse, or
growth — and what contains each mode.

## Reversibility

One-way door or two-way door: what undoing this costs, and what should be done
now to keep it cheap (AX-15).

## Assumptions

What must remain true for this decision to stay correct.

## Evidence

Measurements, incidents, prototypes, or references supporting the choice —
not opinions restated as data.

## Trigger to revisit

The observable condition (metric threshold, scale mark, incident class,
source-of-truth change) that reopens this decision.
