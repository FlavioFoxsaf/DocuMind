"""Testes do backend local (Ollama) sem Ollama de verdade: cliente HTTP com
httpx.MockTransport e clientes falsos para o embedder e o gerador.

O teste real contra o Ollama instalado está em tests/test_integration_ollama.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import numpy as np
import pytest

from src import providers
from src.answering import (
    REFUSAL_TEXT,
    AnsweringError,
    OllamaGenerator,
    _RESPONSE_SCHEMA,
    answer_question,
)
from src.chunking import Chunk
from src.config import load_settings
from src.ollama_client import OllamaClient, OllamaError, missing_models
from src.retrieval import (
    OLLAMA_QUERY_INSTRUCTION,
    OllamaEmbedder,
    RetrievalError,
    build_index,
    retrieve,
)

RAIZ = Path(__file__).resolve().parent.parent
URL = "http://127.0.0.1:11434"


# ---------------------------------------------------------------- cliente HTTP (MockTransport)


CLIENTES: list[OllamaClient] = []


def cliente_http(handler) -> OllamaClient:
    cliente = OllamaClient(URL, timeout=5, transport=httpx.MockTransport(handler))
    CLIENTES.append(cliente)
    return cliente


@pytest.fixture(autouse=True)
def fechar_clientes():
    yield
    while CLIENTES:
        CLIENTES.pop().close()


def test_embed_envia_modelo_e_textos_e_devolve_vetores():
    pedidos = []

    def handler(request):
        pedidos.append((request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"embeddings": [[1.0, 0.0], [0.0, 1.0]]})

    vetores = cliente_http(handler).embed("emb", ["a", "b"])
    assert vetores == [[1.0, 0.0], [0.0, 1.0]]
    assert pedidos == [("/api/embed", {"model": "emb", "input": ["a", "b"]})]


def test_chat_envia_schema_sem_stream_e_com_think():
    pedidos = []

    def handler(request):
        pedidos.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "{}"}, "done_reason": "stop"})

    cliente_http(handler).chat("m", "prompt", {"type": "object"}, {"temperature": 0}, think=True)
    corpo = pedidos[0]
    assert corpo["model"] == "m"
    assert corpo["stream"] is False
    assert corpo["format"] == {"type": "object"}
    assert corpo["think"] is True
    assert corpo["options"] == {"temperature": 0}
    assert corpo["messages"] == [{"role": "user", "content": "prompt"}]


def test_modelo_ausente_vira_instrucao_de_pull():
    def handler(request):
        return httpx.Response(404, json={"error": 'model "x" not found, try pulling it first'})

    with pytest.raises(OllamaError) as erro:
        cliente_http(handler).embed("qwen3-embedding:0.6b", ["a"])
    assert "ollama pull qwen3-embedding:0.6b" in str(erro.value)


def test_servico_desligado_vira_mensagem_clara():
    def handler(request):
        raise httpx.ConnectError("recusada", request=request)

    with pytest.raises(OllamaError) as erro:
        cliente_http(handler).embed("m", ["a"])
    assert "ollama serve" in str(erro.value)
    with pytest.raises(OllamaError):
        cliente_http(handler).list_models()


def test_timeout_vira_mensagem_clara():
    def handler(request):
        raise httpx.ReadTimeout("lento", request=request)

    with pytest.raises(OllamaError) as erro:
        cliente_http(handler).chat("m", "p", {})
    assert "DOCUMIND_OLLAMA_TIMEOUT" in str(erro.value)


def test_erro_http_e_resposta_nao_json_sao_controlados():
    with pytest.raises(OllamaError) as erro:
        cliente_http(lambda r: httpx.Response(500, json={"error": "sem memória"})).embed("m", ["a"])
    assert "500" in str(erro.value)
    with pytest.raises(OllamaError):
        cliente_http(lambda r: httpx.Response(200, text="não é json")).embed("m", ["a"])


def test_missing_models_aceita_sufixo_latest():
    def handler(request):
        return httpx.Response(200, json={"models": [{"name": "qwen3:8b"}, {"name": "embed:latest"}]})

    cliente = cliente_http(handler)
    assert cliente.list_models() == {"qwen3:8b", "embed:latest"}
    assert missing_models(cliente, ["qwen3:8b", "embed", "outro:1b"]) == ["outro:1b"]


# ---------------------------------------------------------------- clientes falsos


class OllamaFalso:
    """Imita OllamaClient: embed com vetores simples e chat com resposta configurável."""

    def __init__(self, resposta=None, erro=None, vetores="padrao", instalados=("gen", "emb")):
        self.resposta = resposta
        self.erro = erro
        self.vetores = vetores
        self.instalados = set(instalados)
        self.embeds: list[tuple[str, list[str]]] = []
        self.chats: list[dict] = []

    def close(self):
        pass

    def list_models(self):
        if self.erro:
            raise self.erro
        return self.instalados

    def embed(self, model, texts):
        self.embeds.append((model, list(texts)))
        if self.erro:
            raise self.erro
        if self.vetores != "padrao":
            return self.vetores
        return [[1.0 + len(t) % 3, 1.0, float("piscina" in t.lower())] for t in texts]

    def chat(self, model, prompt, schema, options=None, think=False):
        self.chats.append({"model": model, "prompt": prompt, "schema": schema,
                           "options": options, "think": think})
        if self.erro:
            raise self.erro
        return self.resposta


def resposta_chat(conteudo, done="stop"):
    return {"message": {"content": conteudo, "thinking": "raciocínio interno"}, "done_reason": done}


# ---------------------------------------------------------------- OllamaEmbedder


def test_embedder_lotes_em_ordem_com_o_mesmo_modelo():
    cliente = OllamaFalso()
    embedder = OllamaEmbedder(cliente, "emb", batch_size=2)
    matriz = embedder.embed_documents(["a", "bb", "ccc", "d", "e"])
    assert matriz.shape == (5, 3) and matriz.dtype == np.float32
    assert [lote for _, lote in cliente.embeds] == [["a", "bb"], ["ccc", "d"], ["e"]]
    embedder.embed_query("Qual o horário?")
    modelos = {modelo for modelo, _ in cliente.embeds}
    assert modelos == {"emb"}  # documentos e perguntas no mesmo modelo
    assert cliente.embeds[-1][1] == [OLLAMA_QUERY_INSTRUCTION + "Qual o horário?"]
    assert embedder.identity == "ollama:emb"


def test_embedder_lista_vazia_nao_chama_o_ollama():
    cliente = OllamaFalso()
    assert OllamaEmbedder(cliente, "emb").embed_documents([]).shape == (0, 0)
    assert cliente.embeds == []


@pytest.mark.parametrize(
    "vetores",
    [
        [[1.0, 2.0]],  # contagem errada (2 textos)
        [[1.0, 2.0], [1.0]],  # dimensões diferentes
        [[1.0, float("nan")], [1.0, 2.0]],  # NaN
        [[1.0, None], [1.0, 2.0]],  # valor ausente
        None,  # resposta sem embeddings
        [None, [1.0, 2.0]],  # vetor ausente
    ],
)
def test_embedder_recusa_respostas_invalidas(vetores):
    with pytest.raises(RetrievalError):
        OllamaEmbedder(OllamaFalso(vetores=vetores), "emb").embed_documents(["a", "b"])


def test_embedder_converte_erro_do_ollama():
    cliente = OllamaFalso(erro=OllamaError("O Ollama não está em execução."))
    with pytest.raises(RetrievalError) as erro:
        OllamaEmbedder(cliente, "emb").embed_query("x")
    assert "não está em execução" in str(erro.value)
    assert isinstance(erro.value.__cause__, OllamaError)


def chunk(i: int, texto: str) -> Chunk:
    return Chunk(chunk_id=f"S1-P{i}-C1", source_name="a.pdf", page_number=i, text=texto)


CHUNKS = [chunk(1, "A piscina abre às 8h."), chunk(2, "A taxa é R$ 80,00."), chunk(3, "Vagas: 1.")]


def test_indice_guarda_o_modelo_e_recusa_busca_com_outro_modelo():
    indice = build_index(CHUNKS, OllamaEmbedder(OllamaFalso(), "emb-a"))
    assert indice.embedder_id == "ollama:emb-a"
    # Mesma dimensão, modelo diferente: a busca tem de ser recusada, não "funcionar".
    with pytest.raises(RetrievalError) as erro:
        retrieve(indice, "piscina", OllamaEmbedder(OllamaFalso(), "emb-b"))
    assert "Processar" in str(erro.value)
    assert retrieve(indice, "piscina", OllamaEmbedder(OllamaFalso(), "emb-a"))


# ---------------------------------------------------------------- OllamaGenerator e fluxo


def perguntar(resposta=None, erro=None, **kwargs):
    embedder = OllamaEmbedder(OllamaFalso(), "emb")
    indice = build_index(CHUNKS, embedder)
    cliente = OllamaFalso(resposta=resposta, erro=erro)
    gerador = OllamaGenerator(cliente, "gen", **kwargs)
    return answer_question("Qual o horário da piscina?", indice, embedder, gerador), cliente


def test_fluxo_local_com_resposta_valida():
    resposta = resposta_chat(json.dumps(
        {"status": "answered", "answer": "Abre às 8h.", "citations": ["S1-P1-C1"]}
    ))
    answer, cliente = perguntar(resposta)
    assert answer.found and answer.text == "Abre às 8h."
    assert [s.chunk.chunk_id for s in answer.sources] == ["S1-P1-C1"]
    chamada = cliente.chats[0]
    assert chamada["schema"] == _RESPONSE_SCHEMA
    assert chamada["think"] is True  # padrão: raciocínio ligado
    # Recomendação do Qwen3 com raciocínio: sem decodificação gulosa, seed fixa e teto.
    assert chamada["options"]["temperature"] == 0.6
    assert chamada["options"]["seed"] == 42
    assert chamada["options"]["num_predict"] > 0
    assert '<trecho id="S1-P1-C1"' in chamada["prompt"]
    assert "raciocínio interno" not in answer.text  # o thinking é descartado


def test_raciocinio_pode_ser_desligado():
    resposta = resposta_chat('{"status": "not_found", "answer": "", "citations": []}')
    _, cliente = perguntar(resposta, think=False)
    assert cliente.chats[0]["think"] is False
    assert cliente.chats[0]["options"]["temperature"] == 0.7  # recomendação sem raciocínio


def test_fluxo_local_not_found_vira_recusa():
    answer, _ = perguntar(resposta_chat('{"status": "not_found", "answer": "", "citations": []}'))
    assert not answer.found and answer.text == REFUSAL_TEXT
    assert answer.refusal_reason == "not_found"


def test_fluxo_local_citacao_inventada_vira_recusa():
    resposta = resposta_chat(json.dumps(
        {"status": "answered", "answer": "Inventado.", "citations": ["S9-P9-C9"]}
    ))
    answer, _ = perguntar(resposta)
    assert not answer.found
    assert answer.refusal_reason == "no_valid_citation"
    assert answer.invalid_citations == ("S9-P9-C9",)


def test_fluxo_local_json_invalido_e_erro_controlado():
    with pytest.raises(AnsweringError) as erro:
        perguntar(resposta_chat("isto não é json"))
    assert "formato inesperado" in str(erro.value)


@pytest.mark.parametrize(
    "resposta",
    [resposta_chat(""), resposta_chat("   "), {"message": {}}, {}, {"message": "texto"}],
)
def test_fluxo_local_resposta_vazia_e_erro_controlado(resposta):
    with pytest.raises(AnsweringError):
        perguntar(resposta)


def test_fluxo_local_resposta_cortada_por_tamanho():
    with pytest.raises(AnsweringError) as erro:
        perguntar(resposta_chat('{"status": "answ', done="length"))
    assert "incompleta" in str(erro.value)


def test_fluxo_local_erro_do_ollama_vira_answering_error():
    embedder = OllamaEmbedder(OllamaFalso(), "emb")
    indice = build_index(CHUNKS, embedder)
    gerador = OllamaGenerator(OllamaFalso(erro=OllamaError("O modelo gen não está instalado.")), "gen")
    with pytest.raises(AnsweringError) as erro:
        answer_question("pergunta?", indice, embedder, gerador)
    assert "não está instalado" in str(erro.value)


# ---------------------------------------------------------------- provedores


LOCAL = load_settings(env={"OLLAMA_MODEL": "gen", "OLLAMA_EMBEDDING_MODEL": "emb"})


def test_backend_local_usa_ollama_nos_dois_papeis():
    backend = providers.build_backend(LOCAL, ollama_client=OllamaFalso())
    assert isinstance(backend.embedder, OllamaEmbedder)
    assert isinstance(backend.generator, OllamaGenerator)
    assert "Ollama local" in backend.label and "gen" in backend.label
    assert "não são enviados" in backend.privacy_note


def test_check_local_ready_aponta_modelos_ausentes():
    with pytest.raises(providers.ProviderError) as erro:
        providers.check_local_ready(LOCAL, OllamaFalso(instalados=("gen",)))
    assert "ollama pull emb" in str(erro.value)
    providers.check_local_ready(LOCAL, OllamaFalso())  # tudo instalado: não levanta


def test_check_local_ready_com_ollama_desligado():
    cliente = OllamaFalso(erro=OllamaError("Não foi possível conectar ao Ollama."))
    with pytest.raises(providers.ProviderError) as erro:
        providers.check_local_ready(LOCAL, cliente)
    assert "conectar" in str(erro.value)
