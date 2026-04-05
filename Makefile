.PHONY: init lint test all clean

init:
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check src/ tests/ tools/
	mypy src/

test:
	pytest -v

all: lint test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache .ruff_cache dist build *.egg-info
