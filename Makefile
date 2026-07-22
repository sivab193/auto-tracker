.PHONY: help up down logs build test lint backend frontend

help:
	@echo "AutoTracker — common tasks"
	@echo "  make up        - build & start the full stack (docker compose)"
	@echo "  make down      - stop the stack"
	@echo "  make logs      - tail backend logs"
	@echo "  make test      - run backend tests"
	@echo "  make lint      - run backend ruff + frontend type-check"
	@echo "  make backend   - run the API locally with reload"
	@echo "  make frontend  - run the Vite dev server"

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f backend

build:
	docker compose build

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check app
	cd frontend && npm run lint

backend:
	cd backend && uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev
