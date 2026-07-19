# Engineering Doctrine

This directory is the repository's school of thought: the axioms, data rules,
and default patterns every plan, task, and review is held against. It exists so
agents (and humans) never design "on the fly" — recurring decisions are made
once, here, and individual features either follow the defaults or record a
deliberate, reviewed deviation.

- `engineering-axioms.md` — architecture and engineering axioms (`AX-*`)
- `data-doctrine.md` — data modeling, schema, and migration axioms (`DD-*`)
- `pattern-library.md` — default patterns for recurring problems (`PAT-*`)

## Authority and precedence

Doctrine sits below the constitution and above individual plans: the
constitution says how work is *governed*; doctrine says how systems are
*shaped*; ADRs apply doctrine to this repository's specifics; plans apply ADRs
to one feature. A plan may not contradict an ADR; an ADR may not contradict
doctrine without superseding text here (a control-plane change).

## How deviation works

Doctrine entries are defaults, not laws of physics. Deviating is legitimate —
silently deviating is not. To deviate: write an ADR in `docs/adr/` citing the
axiom or pattern ID being overridden, the reason, and the consequences; a human
approves it; plans then cite the ADR. Reviewers flag any diff that contradicts
doctrine or an accepted ADR without such a citation.

## Enforcement

This directory lives inside `.agents/**`, so it is protected everywhere the
control plane is protected: agents cannot edit it (hook + scope gate +
settings deny), changes require distinct ownership (CODEOWNERS) and trigger
control-plane CI, and `aers.py lint` fails if the doctrine files are missing.
The architect role must cite axiom and pattern IDs in plans; the reviewer role
checks conformance against cited doctrine, not personal taste.
