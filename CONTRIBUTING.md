# Contributing

Humans and agents use the same feature contracts, tests, security controls, and release system.
Behavior-changing work requires a feature pack under `.specify/specs/<feature-id>/` unless classified
as S0 by policy. Pull requests must disclose agent involvement, base and candidate commits, risk tier,
acceptance evidence, scope report, audit report, residual risk, and rollback.

Changes to agent instructions, policies, hooks, schemas, evaluations, workflows, protected tests,
verifier definitions, memory promotion, or skill locks are control-plane changes. They require distinct
ownership and cannot be authored and approved by the same autonomous identity.
