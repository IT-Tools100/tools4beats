SHELL := /bin/bash
PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: help venv install db-up db-down db-reset migrate seed run test test-fast test-ui lint qt-fix

help:
	@echo "make install   — создать venv и установить зависимости"
	@echo "make db-up     — запустить PostgreSQL в Docker"
	@echo "make db-down   — остановить PostgreSQL"
	@echo "make db-reset  — удалить данные БД (ОПАСНО) и поднять заново"
	@echo "make migrate   — применить миграции"
	@echo "make seed      — заполнить справочники (идемпотентно)"
	@echo "make run       — запустить приложение"
	@echo "make test      — unit + integration тесты"
	@echo "make test-ui   — UI-тесты (offscreen)"

venv:
	test -d .venv || python3 -m venv .venv

install: venv
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -e ".[dev]"
	@SITE=$$($(PY) -c "import sysconfig;print(sysconfig.get_paths()['purelib'])"); \
	 echo "$$PWD/src" > "$$SITE/verse.pth"; \
	 chflags -R nohidden .venv 2>/dev/null || true; \
	 echo "Зависимости установлены."

db-up:
	@docker info >/dev/null 2>&1 || { echo "Docker не запущен. Откройте Docker Desktop и повторите."; exit 1; }
	docker compose up -d --wait db

db-down:
	docker compose down

db-reset:
	docker compose down -v
	docker compose up -d --wait db

qt-fix:
	@chflags -R nohidden .venv 2>/dev/null || true

migrate:
	PYTHONPATH=src $(PY) -m alembic upgrade head

seed:
	PYTHONPATH=src $(PY) -m verse.seed

run: qt-fix
	PYTHONPATH=src $(PY) -m verse

test: qt-fix
	PYTHONPATH=src $(PY) -m pytest tests/unit tests/integration tests/migrations -q

test-fast:
	PYTHONPATH=src $(PY) -m pytest tests/unit -q

test-ui: qt-fix
	PYTHONPATH=src QT_QPA_PLATFORM=offscreen $(PY) -m pytest tests/ui -q
