.PHONY: init lint lint_fix test validate quick_validate check_complexity check_links check_docs all clean

init:
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check src/ tests/ tools/
	mypy src/

lint_fix:
	ruff format src/ tests/ tools/
	ruff check --fix src/ tests/ tools/

test:
	pytest -v

validate:
	ruff format --check src/ tests/ tools/
	ruff check src/ tests/ tools/
	mypy src/
	pytest -v -m "not hardware"

quick_validate:
	ruff check src/ tests/ tools/
	mypy src/

check_complexity:
	complexipy src/dpette/ --max-complexity-allowed 15

check_links:
	lychee --config .lychee.toml .

check_docs:
	markdownlint-cli2 "**/*.md" "#node_modules"

all: lint test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache .ruff_cache dist build *.egg-info
