First interview the human for anything ambiguous whose answer would change the spec (scale, dominant quality
attributes, constraints, non-goals, definition of done) — do not encode assumptions as requirements. Then
create or update a feature pack under `.specify/specs/<feature-id>/` using S0/S1/S2 sizing. Complete human prose,
`feature.contract.json`, and `tasks.json`; run `python3 scripts/aers.py lint`; do not implement code in the same role.
For a large plan, an optional HTML rendering (mockups, decision table, risks) makes human review far more
effective — but the typed contract stays the source of truth; the visualization is only a review aid.
