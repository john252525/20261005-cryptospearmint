.PHONY: test paper-e2e paper-e2e-test clean

test:
	.venv/bin/python -m pytest -q tests

paper-e2e:
	.venv/bin/python main.py

paper-e2e-test:
	.venv/bin/python -m pytest -q tests/test_paper_broker.py tests/test_paper_oms_integration.py

clean:
	rm -f risk.db risk.db-wal risk.db-shm
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
