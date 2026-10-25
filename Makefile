# Project Chameleon Makefile
# High-leverage developer & agent entrypoints

SHELL := /bin/bash
ROOT_DIR := $(shell pwd)
VENV_DIR := $(ROOT_DIR)/.venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip
PYTHON_BOOTSTRAP ?= python3.11

.PHONY: help setup verify verify-fonts install-hooks preflight test run agent-check inspect synthetic prepare-dependencies docker-build docker-test clean

help:
	@echo "Project Chameleon Developer & Agent Commands:"
	@echo "  make setup        - Initialize .venv (Python 3.11) and install dependencies"
	@echo "  make verify        - Verify repository governance and implementation wiring"
	@echo "  make verify-fonts  - Verify packaged font and license hashes"
	@echo "  make install-hooks - Install the versioned repository Git hooks"
	@echo "  make preflight    - Verify repository wiring and require the nested engine"
	@echo "  make test         - Run all unit tests via unittest"
	@echo "  make run          - Execute engine.main on all tasks in chameleon/input/"
	@echo "  make inspect      - Inspect generated layouts in terminal using ASCII visualizer"
	@echo "  make synthetic    - Generate varied marketing aspect-ratio synthetic test cases"
	@echo "  make agent-check  - Run local verification gate (not Stage 1 qualification before Gate 1)"
	@echo "  make docker-build - Build the official linux/amd64 Docker image"
	@echo "  make prepare-dependencies - Prepare the verified linux/amd64 Docker wheelhouse"
	@echo "  make docker-test  - Run the Docker container offline with --network none"
	@echo "  make clean        - Remove generated outputs, caches, and temporary files"

setup:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating virtual environment using $(PYTHON_BOOTSTRAP)..."; \
		$(PYTHON_BOOTSTRAP) -m venv $(VENV_DIR); \
	fi
	@$(PYTHON) -c 'import sys; actual = sys.version_info[:2]; actual == (3, 11) or sys.exit(f"Project setup requires Python 3.11; got {sys.version.split()[0]}. Use a fresh VENV_DIR with PYTHON_BOOTSTRAP=python3.11.")'
	@echo "Installing hash-locked Python dependencies and the verified local renderer wheel..."
	@$(PYTHON_BOOTSTRAP) scripts/prepare_dependency_inputs.py --install-local-renderer --python "$(PYTHON)"
	@echo "Environment setup complete."

verify: verify-fonts
	@$(PYTHON_BOOTSTRAP) scripts/verify_repository.py

verify-fonts:
	@$(PYTHON_BOOTSTRAP) scripts/verify_font_provenance.py

install-hooks:
	@mkdir -p .git/hooks
	@ln -sf ../../.githooks/pre-commit .git/hooks/pre-commit
	@echo "Installed .githooks/pre-commit"

preflight:
	@$(PYTHON_BOOTSTRAP) scripts/verify_repository.py --require-engine

test:
	@echo "Running unit tests..."
	@$(PYTHON) -c 'import sys; actual = sys.version_info[:2]; actual == (3, 11) or sys.exit(f"make test requires Python 3.11 for persisted PNG goldens; got {sys.version.split()[0]}")'
	@cd chameleon && $(PYTHON) -m unittest discover -s tests -t . -p 'test_*.py' -v
	@$(PYTHON) -m unittest scripts.test_review_pr -v
	@$(PYTHON) -m unittest scripts.test_qualify_runtime -v
	@$(PYTHON) -m unittest scripts.test_prepare_dependency_inputs -v
	@$(PYTHON) -m unittest scripts.test_font_provenance -v

run:
	@echo "Running engine.main on chameleon/input/..."
	@cd chameleon && $(PYTHON) -m engine.main

inspect:
	@echo "Inspecting output layouts in terminal..."
	@$(PYTHON) scripts/inspect_layout.py chameleon/output/

synthetic:
	@echo "Generating synthetic marketing test cases..."
	@$(PYTHON) scripts/generate_synthetic_cases.py

agent-check: verify test run inspect
	@echo "=========================================="
	@echo "Agent-check PASSED: Local checks complete; this is not Stage 1 qualification before Gate 1."
	@echo "=========================================="

prepare-dependencies:
	@echo "Preparing hash-verified linux/amd64 wheelhouse..."
	@$(PYTHON_BOOTSTRAP) scripts/prepare_dependency_inputs.py --prepare-wheelhouse

docker-build: prepare-dependencies
	@echo "Building linux/amd64 Docker image..."
	@docker buildx build --platform linux/amd64 --load -t chameleon-stage1 chameleon/

docker-test:
	@echo "Running offline container test with --network none..."
	@mkdir -p chameleon/output
	@docker run --rm --network none \
		-v "$(ROOT_DIR)/chameleon/input:/app/input:ro" \
		-v "$(ROOT_DIR)/chameleon/output:/app/output" \
		chameleon-stage1
	@echo "Docker test completed."

clean:
	@rm -rf chameleon/.wheelhouse chameleon/.wheelhouse.tmp-*
	@rm -f chameleon/output/*_output.json chameleon/output/*_output.png \
		chameleon/output/*.tmp chameleon/output/.*_output.commit \
		chameleon/output/.*_output.commit.tmp
	@find chameleon/output -maxdepth 1 -type d \
		-name '.chameleon-quarantine-*' -prune -exec rm -rf {} + 2>/dev/null || true
	@find chameleon/output -maxdepth 1 -type d \
		-name '.*.stage-*' -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Removed the generated dependency wheelhouse."
	@echo "Cleaned generated files, markers, and caches."
