docker compose exec dev uv run alembic revision --autogenerate -m "$1"
docker compose exec dev uv run alembic upgrade head