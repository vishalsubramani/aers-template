# Implementation Plan

## Context and constraints
## Doctrine conformance
<!-- Axioms/patterns this plan relies on (AX-*, DD-*, PAT-*), ADRs applied,
     and any deviation with its approving ADR. No blank citations: if the plan
     touches a boundary, name the boundary patterns; if it touches data, the
     data section below is mandatory. -->
## Impacted components and public contracts
## Data model delta
<!-- New/changed entities, fields, types, constraints; migration plan
     (expand→migrate→contract where breaking, DD-11); backfill strategy;
     data classification of new fields (DD-14); retention/deletion (DD-15).
     Write "none" only when no persisted shape changes. -->
## Dependency order and partitions
## Planned file changes
## Compatibility/migration strategy
## Security and threat analysis
## Test strategy and protected oracle strategy
## Observability and operational readiness
## Rollout, health gates, and rollback
## Risks and mitigations
## Rejected alternatives

Every planned file must be included in one immutable task write scope. Review this plan before implementation.
