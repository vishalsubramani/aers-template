.PHONY: bootstrap check test security evals verify aers-lint review-gate \
        benchmark assess assurance threat-model evaluator-health baseline assure evidence-manifest

bootstrap:
	@echo "Replace with reproducible repository bootstrap."

aers-lint:
	python3 scripts/aers.py lint

# Fail-closed independent-review evidence gate (additive; author-side). Requires a
# candidate-bound independent review for every approved feature at a required risk
# tier. Closes the "implemented outside loop.py, still merged" hole.
review-gate:
	python3 scripts/checks/independent_review_gate.py

check: aers-lint review-gate
	@echo "Add formatter, linter, type, schema, and architecture checks."

test:
	python3 -m unittest discover -s tests -p 'test_*.py'

security:
	@echo "Add secret, SAST, dependency, license, IaC, and policy scanners."

evals:
	python3 scripts/aers.py eval-public

# --- Assurance layer (additive; author-side only, never issues VERIFIED) ------
benchmark:
	python3 scripts/assure.py benchmark

assess:
	python3 scripts/assure.py assess --profile standard

assurance:
	python3 scripts/assure.py assurance

threat-model:
	python3 scripts/assure.py threat-model

evaluator-health:
	python3 scripts/assure.py evaluator-health

baseline:
	python3 scripts/assure.py baseline

# POST-COMMIT artifact: writes only under the gitignored evidence dir; never
# commit the manifest into the candidate it describes (that changes the SHA).
evidence-manifest:
	python3 scripts/assure.py evidence-manifest --profile standard --output .aers-evidence/evidence-manifest.json --release-readiness .aers-evidence/RELEASE-READINESS.md

# Aggregate author-side assurance gates. Strengthens verify; weakens nothing.
assure: benchmark assess assurance threat-model evaluator-health
	@echo "Author-side assurance gates complete. This is not external VERIFIED."

verify: check test security evals assure
	@echo "Author-visible verification complete. This is not external VERIFIED."
