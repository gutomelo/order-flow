"""Leitura de variáveis de ambiente compartilhada pelos módulos de settings.

Execução nativa (fora de containers) lê o `.env` da raiz do repositório. Variáveis já definidas
no ambiente (ex.: pelo Docker Compose ou pela CI) têm precedência sobre o arquivo.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPOSITORY_ROOT = BASE_DIR.parent

env = environ.Env()

if (REPOSITORY_ROOT / ".env").exists():
    env.read_env(str(REPOSITORY_ROOT / ".env"))
