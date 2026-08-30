.PHONY: up down logs harness

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

harness:
	python3 -m venv .venv-harness
	.venv-harness/bin/pip install httpx==0.25.1 pyyaml==6.0.1
	.venv-harness/bin/python harness/runner.py

demo:
	CONFIG_PATH=config/policies.demo.yaml docker compose up -d
	sleep 3
	CONFIG_PATH=config/policies.demo.yaml $(MAKE) harness
