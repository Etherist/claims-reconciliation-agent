# Makefile for Claims Reconciliation Agent

.PHONY: help install test lint format clean docs run setup

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies in virtual env"
	@echo "  make test       - Run pytest with coverage"
	@echo "  make lint       - Run flake8 linter"
	@echo "  make format     - Auto-format code with black"
	@echo "  make typecheck  - Run mypy type checker"
	@echo "  make clean      - Remove cache files and reports"
	@echo "  make docs       - Build documentation with mkdocs"
	@echo "  make run        - Launch Streamlit app"
	@echo "  make setup      - Full project setup"

install:
	pip install -r requirements.txt
	pip install -e ".[dev]"

test:
	pytest --cov=src --cov-report=term --cov-report=html

lint:
	flake8 src/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src/ tests/ --count --exit-zero --max-complexity=10 --max-line-length=88

format:
	black src/ tests/
	isort src/ tests/

typecheck:
	mypy src/

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .mypy_cache .pytest_cache htmlcov .coverage
	rm -rf reports/*.csv reports/*.json reports/*.pdf logs/*.log

docs:
	mkdocs build

run:
	streamlit run src/app/streamlit_app.py

setup:
	bash scripts/setup.sh
