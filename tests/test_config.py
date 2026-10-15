"""Testes do `src/config.py` (contrato `docs/contratos/providers.md`).

Nenhum teste lê o `.env` real: quando `env=None`, `load_dotenv` é trocado por um espião.
"""

from __future__ import annotations

import dataclasses
from types import MappingProxyType

import dotenv
import pytest

import src.config as config_mod
from src.config import (
    DEFAULT_OLLAMA_EMBEDDING_MODEL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_TIMEOUT,
    DEFAULT_OLLAMA_URL,
    ConfigError,
    Settings,
    load_settings,
)

VARIAVEIS = (
    "OLLAMA_MODEL",
    "OLLAMA_EMBEDDING_MODEL",
    "DOCUMIND_OLLAMA_URL",
    "DOCUMIND_OLLAMA_TIMEOUT",
    "DOCUMIND_OLLAMA_THINK",
)


class EspiaoDotenv:
    """Substitui `load_dotenv` para não tocar no `.env` real e registrar as chamadas."""

    def __init__(self, falhar: bool = False) -> None:
        self.falhar = falhar
        self.chamadas: list[tuple[tuple, dict]] = []

    def __call__(self, *args, **kwargs):
        self.chamadas.append((args, kwargs))
        if self.falhar:
            raise AssertionError("load_dotenv não deveria ser chamado com env explícito")
        return False


def instalar_espiao(monkeypatch: pytest.MonkeyPatch, falhar: bool = False) -> EspiaoDotenv:
    espiao = EspiaoDotenv(falhar=falhar)
    monkeypatch.setattr(dotenv, "load_dotenv", espiao)
    monkeypatch.setattr(config_mod, "load_dotenv", espiao, raising=False)
    return espiao


@pytest.fixture
def ambiente_limpo(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for nome in VARIAVEIS:
        monkeypatch.delenv(nome, raising=False)
    return monkeypatch


# ---------------------------------------------------------------- padrões


def test_padroes_do_contrato():
    assert DEFAULT_OLLAMA_MODEL == "qwen3:14b"
    assert DEFAULT_OLLAMA_EMBEDDING_MODEL == "qwen3-embedding:0.6b"
    assert DEFAULT_OLLAMA_URL == "http://127.0.0.1:11434"
    assert issubclass(ConfigError, Exception)


def test_sem_nenhuma_variavel_usa_os_padroes():
    settings = load_settings(env={})
    assert settings == Settings(
        model=DEFAULT_OLLAMA_MODEL,
        embedding_model=DEFAULT_OLLAMA_EMBEDDING_MODEL,
        ollama_url=DEFAULT_OLLAMA_URL,
        timeout=DEFAULT_OLLAMA_TIMEOUT,
        think=True,
    )


def test_settings_tem_os_campos_do_contrato_e_e_imutavel():
    nomes = {campo.name for campo in dataclasses.fields(Settings)}
    assert nomes == {"model", "embedding_model", "ollama_url", "timeout", "think"}
    settings = load_settings(env={})
    with pytest.raises(dataclasses.FrozenInstanceError):
        settings.model = "outro"  # type: ignore[misc]


def test_variaveis_antigas_do_gemini_sao_ignoradas():
    """O Gemini foi removido: essas variáveis, se sobrarem no .env, não mudam nada."""
    env = {"GEMINI_API_KEY": "AIza-sobra", "GEMINI_MODEL": "g", "DOCUMIND_PROVIDER": "gemini"}
    settings = load_settings(env=env)
    assert settings == load_settings(env={})
    assert "AIza-sobra" not in repr(settings)


# ---------------------------------------------------------------- valores personalizados


def test_valores_personalizados_com_strip():
    settings = load_settings(
        env={
            "OLLAMA_MODEL": " qwen3:14b ",
            "OLLAMA_EMBEDDING_MODEL": "\tembed-x\n",
            "DOCUMIND_OLLAMA_URL": "http://localhost:11500/",
            "DOCUMIND_OLLAMA_TIMEOUT": "30",
            "DOCUMIND_OLLAMA_THINK": "false",
        }
    )
    assert settings.model == "qwen3:14b"
    assert settings.embedding_model == "embed-x"
    assert settings.ollama_url == "http://localhost:11500"
    assert settings.timeout == 30.0
    assert settings.think is False


@pytest.mark.parametrize("valor", ["", "   "])
def test_modelos_vazios_usam_os_padroes(valor):
    settings = load_settings(env={"OLLAMA_MODEL": valor, "OLLAMA_EMBEDDING_MODEL": valor})
    assert (settings.model, settings.embedding_model) == (
        DEFAULT_OLLAMA_MODEL, DEFAULT_OLLAMA_EMBEDDING_MODEL,
    )


# ---------------------------------------------------------------- validação


@pytest.mark.parametrize(
    "url",
    ["http://192.168.0.10:11434", "https://ollama.com", "http://exemplo.com:11434", "ftp://localhost"],
)
def test_url_fora_da_maquina_e_recusada(url):
    with pytest.raises(ConfigError) as erro:
        load_settings(env={"DOCUMIND_OLLAMA_URL": url})
    assert "DOCUMIND_OLLAMA_URL" in str(erro.value)


@pytest.mark.parametrize("url", ["http://127.0.0.1:11434", "http://localhost:1234", "http://[::1]:11434"])
def test_url_local_e_aceita(url):
    assert load_settings(env={"DOCUMIND_OLLAMA_URL": url}).ollama_url == url


@pytest.mark.parametrize("valor", ["0", "-5", "abc"])
def test_timeout_invalido_e_recusado(valor):
    with pytest.raises(ConfigError):
        load_settings(env={"DOCUMIND_OLLAMA_TIMEOUT": valor})


def test_raciocinio_ligado_por_padrao_e_configuravel():
    assert load_settings(env={}).think is True
    assert load_settings(env={"DOCUMIND_OLLAMA_THINK": "false"}).think is False
    assert load_settings(env={"DOCUMIND_OLLAMA_THINK": "Sim"}).think is True
    with pytest.raises(ConfigError):
        load_settings(env={"DOCUMIND_OLLAMA_THINK": "talvez"})


# ---------------------------------------------------------------- .env e ambiente


def test_env_explicito_nao_le_os_environ_nem_o_dotenv(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "modelo-do-ambiente")
    espiao = instalar_espiao(monkeypatch, falhar=True)
    assert load_settings(env={}).model == DEFAULT_OLLAMA_MODEL
    assert load_settings(env=MappingProxyType({"OLLAMA_MODEL": "m"})).model == "m"
    assert espiao.chamadas == []


def test_env_none_le_os_environ_e_chama_dotenv_sem_sobrescrever(ambiente_limpo):
    espiao = instalar_espiao(ambiente_limpo)
    ambiente_limpo.setenv("OLLAMA_MODEL", "modelo-x")
    assert load_settings().model == "modelo-x"
    assert len(espiao.chamadas) == 1
    _, kwargs = espiao.chamadas[0]
    assert kwargs.get("override", False) is False


def test_env_none_sem_variaveis_usa_os_padroes(ambiente_limpo):
    instalar_espiao(ambiente_limpo)
    assert load_settings() == load_settings(env={})
