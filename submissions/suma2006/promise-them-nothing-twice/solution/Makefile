.PHONY: up down logs harness

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

harness:
	python3 -m venv .venv-harness
	.venv-harness/bin/pip install httpx==0.25.1
	.venv-harness/bin/python harness/runner.py
