PYTHON ?= python
ENV = PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src

.PHONY: validate validate-full reproduce test security verify clean-room

validate:
	$(ENV) $(PYTHON) -B workflows/validate_installation.py

validate-full:
	$(ENV) $(PYTHON) -B workflows/validate_installation.py --full

reproduce:
	$(ENV) $(PYTHON) -B workflows/reproduce_public_results.py --output-root reproduced_outputs

test:
	$(ENV) $(PYTHON) -B -m unittest discover -s tests -v

security:
	$(ENV) $(PYTHON) -B tools/security_scan.py --root .

verify:
	$(ENV) $(PYTHON) -B tools/verify_reference_outputs.py

clean-room:
	$(ENV) $(PYTHON) -B tools/clean_room_test.py --repository-root .
