help:
	@echo "Available Makefile commands:"
	@echo "  run        : Build and start project"
	@echo "  lint       : Run linters to check code quality"
	@echo "  lint-fix   : Run linters and auto-fix issues (if possible)"
	@echo "  test       : Run tests"
	@echo "  migration  : Generate a new alembic migration"
	@echo "  migrate    : Update database with alembic migrations"

run:
	docker-compose up -d --build

lint:
	ruff check .

lint-fix:
	ruff format .
	ruff check --fix .

test:
	docker-compose run persistent_credentials_pool pytest .

migration:
	docker-compose exec persistent_credentials_pool alembic revision --autogenerate -m "$(m)"

migrate:
	docker-compose exec persistent_credentials_pool alembic upgrade head
