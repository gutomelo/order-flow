# OrderFlow — Backend

API Django + DRF (Modular Monolith) e workers Celery.

- Arquitetura: [../docs/architecture/backend.md](../docs/architecture/backend.md)
- Ambiente local: [../docs/development/local-development.md](../docs/development/local-development.md)

```bash
moon run backend:check     # lint + format-check + typecheck + test
moon run backend:dev       # runserver em :8000 (requer postgres/redis/rabbitmq)
```
