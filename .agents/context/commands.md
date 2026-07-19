# Command Catalog

| Purpose | Command | Network | Expected evidence |
|---|---|---|---|
| Bootstrap | `make bootstrap` | allowlisted only | deterministic environment |
| Static checks | `make check` | denied | reports + exit 0 |
| Tests | `make test` | denied | machine test report |
| Security | `make security` | allowlisted scanner DB only | scanner reports |
| Agent evals | `make evals` | denied | scored evaluation report |
| Author verify | `make verify` | denied | author-visible report |

Autonomous task contracts use JSON argv arrays rather than shell strings. Document timeouts, services,
fixtures, and expected nondeterminism here.
