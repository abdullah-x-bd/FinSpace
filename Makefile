.PHONY: test quality evidence evidence-quick verify

test:
	pytest

quality:
	ruff check src tests experiments
	mypy src/finspace/schema.py src/finspace/compiler.py src/finspace/space.py src/finspace/replay.py src/finspace/runner.py src/finspace/weighted.py src/finspace/allocation.py src/finspace/evolution.py src/finspace/shrink.py src/finspace/identity.py src/finspace/campaign.py src/finspace/mutations.py src/finspace/artifact.py src/finspace/cluster.py

test-evidence:
	pytest tests/test_properties.py tests/test_adversarial_schemas.py tests/test_negative_controls.py tests/test_weighted.py tests/test_allocation_final.py tests/test_constraints_final.py tests/test_evolution_final.py tests/test_shrink_identity_final.py tests/test_campaign_artifact_final.py tests/test_mutations_cluster_retry_final.py

evidence:
	python -m experiments.final_reproduce --output evidence/generated

evidence-quick:
	python -m experiments.final_reproduce --output evidence/generated --quick

verify: quality test evidence-quick
