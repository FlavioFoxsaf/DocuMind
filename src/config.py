"""Leitura da configuração dos modelos locais (Ollama).

O DocuMind roda inteiro nesta máquina: embeddings e respostas vêm do Ollama em
http://127.0.0.1:11434. Não há chave de API nem serviço externo. A URL só aceita endereços
locais, e é isso que garante que os documentos não saem da máquina.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
# qwen3:14b em vez do 8b: na matriz difícil de 27/09 fez 48/48 contra 45/48 do 8b (o 8b
# não fechava a conta da multa por dano). Custa ~1,5x o tempo; o usuário prioriza precisão.
DEFAULT_OLLAMA_MODEL = "qwen3:14b"
DEFAULT_OLLAMA_EMBEDDING_MODEL = "qwen3-embedding:0.6b"
DEFAULT_OLLAMA_TIMEOUT = 180.0  # segundos; a primeira resposta inclui carregar o modelo

# Só endereços da própria máquina: é isso que garante que os documentos não saem dela.
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_TRUE = {"1", "true", "sim", "yes", "on"}
_FALSE = {"0", "false", "nao", "não", "no", "off"}


class ConfigError(Exception):
    """Mensagem pronta para o usuário."""


@dataclass(frozen=True)
class Settings:
    model: str  # modelo de geração
    embedding_model: str  # modelo de embedding (trechos e perguntas)
    ollama_url: str = DEFAULT_OLLAMA_URL
    timeout: float = DEFAULT_OLLAMA_TIMEOUT
    # Raciocínio do Qwen3 antes da resposta: mais lento (3–8 s), mas acertou as perguntas
    # que combinam trechos, que o modo direto errou nos testes de 27/09.
    think: bool = True


def _read(env: Mapping[str, str], name: str) -> str:
    """Valor da variável sem espaços nas pontas; ausente conta como vazio."""
    return (env.get(name) or "").strip()


def _local_url(value: str) -> str:
    """Aceita só URLs http(s) que apontem para esta máquina."""
    url = value.rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in _LOCAL_HOSTS:
        raise ConfigError(
            f"DOCUMIND_OLLAMA_URL deve apontar para esta máquina (ex.: {DEFAULT_OLLAMA_URL}). "
            "O DocuMind não envia documentos para outros endereços."
        )
    return url


def _timeout(value: str) -> float:
    if not value:
        return DEFAULT_OLLAMA_TIMEOUT
    try:
        seconds = float(value)
    except ValueError:
        seconds = 0.0
    if seconds <= 0:
        raise ConfigError("DOCUMIND_OLLAMA_TIMEOUT deve ser um número de segundos maior que zero.")
    return seconds


def _flag(value: str, name: str, default: bool) -> bool:
    value = value.lower()
    if not value:
        return default
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ConfigError(f"{name} deve ser true ou false.")


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Monta as configurações a partir de `env` ou, se omitido, do .env e do ambiente.

    Com `env` informado, só ele é lido: os testes não dependem do .env da máquina.
    Todas as variáveis são opcionais; sem nenhuma, valem os padrões acima.
    """
    if env is None:
        # override=False: uma variável já definida no sistema vale mais que o .env.
        load_dotenv(override=False)
        env = os.environ

    return Settings(
        model=_read(env, "OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL,
        embedding_model=_read(env, "OLLAMA_EMBEDDING_MODEL") or DEFAULT_OLLAMA_EMBEDDING_MODEL,
        ollama_url=_local_url(_read(env, "DOCUMIND_OLLAMA_URL") or DEFAULT_OLLAMA_URL),
        timeout=_timeout(_read(env, "DOCUMIND_OLLAMA_TIMEOUT")),
        think=_flag(_read(env, "DOCUMIND_OLLAMA_THINK"), "DOCUMIND_OLLAMA_THINK", True),
    )
