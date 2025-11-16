.PHONY: help build up down restart logs shell clean test edit

help:
	@echo "Available commands:"
	@echo "  make build    - Build Docker images"
	@echo "  make up       - Start services (builds if needed)"
	@echo "  make down     - Stop and remove containers"
	@echo "  make restart  - Restart all services"
	@echo "  make logs     - Show logs (follow mode)"
	@echo "  make shell    - Open shell in app container"
	@echo "  make clean    - Remove containers, volumes, and images"
	@echo "  make edit     - Run the text editor (opens untitled file)"
	@echo "  make edit FILE=<filename> - Open specific file"

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

edit:
	@docker compose run --rm app python txtarea.py $(filter-out $@,$(MAKECMDGOALS))

%:
	@:

test:
	docker compose run --rm app python -c "import textual; import httpx; print('Dependencies OK')"