.PHONY: test quality evidence evidence-quick verify

test:
	pytest

quality:
	ruff check src tests experiments
	mypy src

test-evidence:
	pytest tests/test_properties.py tests/test_adversarial_schemas.py tests/test_negative_controls.py

evidence:
	python -m experiments.reproduce --output evidence/generated

evidence-quick:
	python -m experiments.reproduce --output evidence/generated --quick

verify: quality test evidence-quick
