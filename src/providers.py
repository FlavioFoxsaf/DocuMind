"""Monta o par (embedder, gerador) do Ollama local a partir de Settings.

Tudo roda na máquina, via http://127.0.0.1:11434, sem chave. Se o Ollama estiver
desligado ou faltar um modelo, check_local_ready explica como corrigir; nada é baixado
automaticamente.
"""

from dataclasses import dataclass

# Classes acessadas pelo módulo (retrieval.OllamaEmbedder...) na hora da chamada, para que
# os testes possam substituí-las por versões falsas.
from src import answering, retrieval
from src.answering import Generator
from src.config import Settings
from src.ollama_client import OllamaClient, OllamaError, missing_models
from src.retrieval import Embedder


class ProviderError(Exception):
    """Mensagem pronta para o usuário, com a instrução de correção."""


@dataclass(frozen=True)
class Backend:
    embedder: Embedder
    generator: Generator
    label: str  # o que mostrar na tela: os modelos em uso
    privacy_note: str


PRIVACY_NOTE = (
    "🔒 Tudo roda nesta máquina: os PDFs, os trechos, os embeddings e as perguntas são "
    "processados pelo Ollama local e não são enviados para a internet. Nada é gravado em disco."
)


def build_backend(settings: Settings, *, ollama_client=None) -> Backend:
    """Cria embedder e gerador locais; o cliente pode vir pronto (testes)."""
    client = ollama_client or OllamaClient(settings.ollama_url, settings.timeout)
    return Backend(
        embedder=retrieval.OllamaEmbedder(client, settings.embedding_model),
        generator=answering.OllamaGenerator(client, settings.model, think=settings.think),
        label=f"Ollama local · {settings.model} + {settings.embedding_model}",
        privacy_note=PRIVACY_NOTE,
    )


def check_local_ready(settings: Settings, client=None) -> None:
    """Confere se o Ollama responde e se os dois modelos estão instalados.

    Não baixa nada: a instalação dos modelos é um passo explícito do usuário.
    """
    own_client = client is None  # o app chama isto a cada interação: fechar a conexão
    client = client or OllamaClient(settings.ollama_url, settings.timeout)
    try:
        missing = missing_models(client, [settings.model, settings.embedding_model])
    except OllamaError as error:
        raise ProviderError(str(error)) from error
    finally:
        if own_client:
            client.close()
    if missing:
        commands = "; ".join(f"ollama pull {model}" for model in missing)
        raise ProviderError(
            f"Modelo(s) não instalado(s) no Ollama: {', '.join(missing)}. "
            f"Rode no terminal: {commands}"
        )
