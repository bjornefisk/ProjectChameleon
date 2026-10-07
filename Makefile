# Project Chameleon Makefile
# High-leverage developer & agent entrypoints

SHELL := /bin/bash
ROOT_DIR := $(shell pwd)
VENV_DIR := $(ROOT_DIR)/.venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

.PHONY: help setup test run agent-check inspect synthetic docker-build docker-test clean

help:
	@echo "Project Chameleon Developer & Agent Commands:"
	@echo "  make setup        - Initialize .venv (Python 3.11) and install dependencies"
	@echo "  make test         - Run all unit tests via unittest"
	@echo "  make run          - Execute engine.main on all tasks in chameleon/input/"
	@echo "  make inspect      - Inspect generated layouts in terminal using ASCII visualizer"
	@echo "  make synthetic    - Generate varied marketing aspect-ratio synthetic test cases"
	@echo "  make agent-check  - Complete verification gate (tests + run + layout inspection)"
	@echo "  make docker-build - Build the official linux/amd64 Docker image"
	@echo "  make docker-test  - Run the Docker container offline with --network none"
	@echo "  make clean        - Remove generated outputs, caches, and temporary files"

setup:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating virtual environment using /opt/homebrew/bin/python3.11..."; \
		/opt/homebrew/bin/python3.11 -m venv $(VENV_DIR); \
	fi
	@echo "Installing dependencies from chameleon/requirements.txt..."
	@$(PIP) install --upgrade pip
	@$(PIP) install -r chameleon/requirements.txt
	@echo "Environment setup complete."

test:
	@echo "Running unit tests..."
	@cd chameleon && $(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

run:
	@echo "Running engine.main on chameleon/input/..."
	@cd chameleon && $(PYTHON) -m engine.main

inspect:
	@echo "Inspecting output layouts in terminal..."
	@$(PYTHON) scripts/inspect_layout.py chameleon/output/

synthetic:
	@echo "Generating synthetic marketing test cases..."
	@$(PYTHON) scripts/generate_synthetic_cases.py

agent-check: test run inspect
	@echo "=========================================="
	@echo "Agent-check PASSED: All gates verified."
	@echo "=========================================="

docker-build:
	@echo "Building linux/amd64 Docker image..."
	@docker buildx build --platform linux/amd64 -t chameleon-stage1 chameleon/

docker-test:
	@echo "Running offline container test with --network none..."
	@mkdir -p chameleon/output
	@docker run --rm --network none \
		-v "$(ROOT_DIR)/chameleon/input:/app/input" \
		-v "$(ROOT_DIR)/chameleon/output:/app/output" \
		chameleon-stage1
	@echo "Docker test completed."

clean:
	@rm -f chameleon/output/*_output.json chameleon/output/*_output.png
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaned generated files and caches."
