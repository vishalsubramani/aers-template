# Write Boundaries

Default deny. The immutable task contract lists exact glob scopes. Sensitive surfaces include authentication,
authorization, secrets, cryptography, data migrations, schemas, infrastructure, CI, deployments, agent
policy, hooks, evals, memory promotion, skills, generated code, lock files, and release controls.

Co-located tests such as `foo_test.go`, `foo.spec.ts`, and `foo.test.py` are tests even when outside `tests/`.
Symlinks are checked to prevent writes escaping an allowed directory.
