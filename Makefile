.PHONY: doctor test examples verify-artifacts calibrate-v02 sync-results dev-up dev-shell dev-test

doctor:
	PYTHONPATH=src python3 -m svgap doctor

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

examples:
	PYTHONPATH=src python3 -m unittest tests.test_examples -v

verify-artifacts:
	PYTHONPATH=src python3 scripts/verify_public_artifacts.py

calibrate-v02:
	PYTHONPATH=src python3 -m unittest tests.test_pilot.PilotTests.test_reset_v02_references_calibrate_every_task -v

sync-results:
	PYTHONPATH=src python3 scripts/sync_results.py

dev-up:
	docker compose up -d

dev-shell:
	docker compose exec svgap-dev bash

dev-test:
	docker compose exec svgap-dev bash -c "test -d .venv || python -m venv .venv; .venv/bin/python -m pip install -e '.[dev]' -q && .venv/bin/python -m unittest discover -s tests -v"
