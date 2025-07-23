CURRENT_USER := $(shell whoami)

# Python virtual environment
VENV_DIR=./.venv
PYTHON := $(shell uv venv python)

check-uv-installed: ## Check if uv is installed
	@command -v uv >/dev/null 2>&1 || { echo >&2 "uv is required but it's not installed. run 'brew install uv' or 'pip install uv' to get the latest version"; exit 1; }

dev-setup: ## Set up development environment
	@echo "Setting up development environment..."
	uv venv --python 3.13
	@echo "Activating virtual environment and installing dependencies..."
	uv pip install ".[dev]"
	@echo "Development environment setup complete!"
	@echo "To activate the virtual environment, run: source .venv/bin/activate"

uv-clean-cache: ## Clean UV cache
	@echo "🚀 Cleaning UV cache"
	uv cache clean

test: sync## Run tests
	uv run pytest tests/ -v

run: sync ## Run the application
	@. ./scripts/set_env_vars.sh && uv run python app/agent_runner.py

sync: check-uv-installed ## Sync dependencies
	uv sync --all-extras

coverage: ## Run tests with coverage report
	uv run pytest --cov=app/ --cov-report=html --cov-report=term-missing

clean-local: ## Clean local environment
	rm -rf .venv
	rm -f uv.lock
	rm -rf venv

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
