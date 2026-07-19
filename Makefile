.PHONY: bootstrap check test security evals verify aers-lint

bootstrap:
	@echo "Replace with reproducible repository bootstrap."

aers-lint:
	python3 scripts/aers.py lint

check: aers-lint
	@echo "Add formatter, linter, type, schema, and architecture checks."

test:
	python3 -m unittest discover -s tests -p 'test_*.py'

security:
	@echo "Add secret, SAST, dependency, license, IaC, and policy scanners."

evals:
	python3 scripts/aers.py eval-public

verify: check test security evals
	@echo "Author-visible verification complete. This is not external VERIFIED."
