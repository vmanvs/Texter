.PHONY: help build up down restart logs shell clean test edit install-local run-local

help:
	@echo "Available commands:"
	@echo ""
	@echo "Docker commands:"
	@echo "  make build           - Build Docker images"
	@echo "  make up              - Start services (builds if needed)"
	@echo "  make down            - Stop and remove containers"
	@echo "  make restart         - Restart all services"
	@echo "  make logs            - Show logs (follow mode)"
	@echo "  make shell           - Open shell in app container"
	@echo "  make clean           - Remove containers, volumes, and images"
	@echo "  make edit [filename] - Run the text editor in Docker (optional filename)"
	@echo "  make test            - Test dependencies in Docker"
	@echo ""
	@echo "Local commands (without Docker):"
	@echo "  make install-local      - Install Python dependencies locally"
	@echo "  make run-local [filename] - Run the text editor locally (optional filename)"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart: down up

logs:
	docker compose logs -f

shell:
	docker compose exec app /bin/sh

clean:
	docker compose down -v --rmi local
	@echo "Cleaned up containers, volumes, and local images"

test:
	docker compose run --rm app python -c "import textual; import httpx; print('Dependencies OK')"

edit:
	@docker compose run --rm app python txtarea.py $(filter-out $@,$(MAKECMDGOALS))

install-local:
	pip install -r requirements.txt
	@echo "Dependencies installed locally"

run-local:
	@python txtarea.py $(filter-out $@,$(MAKECMDGOALS))

%:
	@: