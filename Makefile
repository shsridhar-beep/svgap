.PHONY: doctor test examples verify-artifacts calibrate-v02

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
