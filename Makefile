# Atalhos de DX. Cada alvo apenas delega: tarefas de engenharia → Moonrepo; runtime → Docker Compose.
# Nenhuma lógica de pipeline vive aqui (docs/architecture/monorepo.md).

.PHONY: help dev up stop down logs ps test lint typecheck check build format migrate makemigrations shell createsuperuser

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

dev: ## Sobe o ambiente completo (foreground)
	docker compose up

up: ## Sobe o ambiente completo em background e aguarda ficar saudável
	docker compose up -d --wait

stop: ## Para os containers (mantém dados)
	docker compose stop

down: ## Remove os containers (mantém volumes)
	docker compose down

logs: ## Acompanha os logs
	docker compose logs -f

ps: ## Estado dos serviços
	docker compose ps

test: ## Testes de todos os projetos
	moon run :test

lint: ## Lint de todos os projetos
	moon run :lint

typecheck: ## Type-check de todos os projetos
	moon run :typecheck

check: ## lint + format-check + typecheck + test
	moon run :check

build: ## Build de todos os projetos
	moon run :build

format: ## Formata o código
	moon run :format

migrate: ## Aplica migrations no container do backend
	docker compose exec backend python manage.py migrate

makemigrations: ## Gera migrations (uso: make makemigrations app=orders name=add_x)
	docker compose exec backend python manage.py makemigrations $(app) --name $(name)

shell: ## Shell do Django no container do backend
	docker compose exec backend python manage.py shell

createsuperuser: ## Cria um superusuário
	docker compose exec backend python manage.py createsuperuser
