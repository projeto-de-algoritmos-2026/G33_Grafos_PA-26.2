VENV := .venv
BIN := $(shell if [ -d "$(VENV)/bin" ]; then echo "$(VENV)/bin/"; fi)

PYTHON := $(BIN)python
STREAMLIT := $(BIN)streamlit
RUFF := $(BIN)ruff

.PHONY: install run lint format build check clean help

help:
	@echo "Comandos disponíveis no SkillRoute:"
	@echo "  make install - Instala dependências do projeto"
	@echo "  make run     - Inicia a aplicação Streamlit"
	@echo "  make lint    - Executa o linter (Ruff)"
	@echo "  make format  - Aplica a formatação de código (Ruff)"
	@echo "  make build   - Gera o pacote de distribuição Python"
	@echo "  make check   - Executa lint, formato e build do pacote"
	@echo "  make clean   - Remove arquivos temporários de build e caches"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

run:
	$(STREAMLIT) run app.py

lint:
	$(RUFF) check .

format:
	$(RUFF) format .

build:
	$(PYTHON) -m build

check:
	$(RUFF) check .
	$(RUFF) format --check .
	$(PYTHON) -m build

clean:
	rm -rf build/ dist/ *.egg-info/ .ruff_cache/ .pytest_cache/ .coverage htmlcov/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
