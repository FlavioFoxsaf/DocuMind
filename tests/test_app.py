"""Testes de interface (caixa-preta) do `app.py`, escritos a partir de
`docs/contratos/app.md`, com `streamlit.testing.v1.AppTest` (streamlit 1.64).

Nada usa rede nem o Ollama de verdade:
- `src.config.load_settings` devolve `Settings` fixas, e `load_dotenv` vira no-op, para o
  `.env` da máquina nunca ser lido;
- `src.providers.OllamaClient` é um cliente falso: lista os modelos "instalados",
  responde `chat` citando o primeiro trecho do prompt e falha se alguém tentar gerar
  embeddings por ele;
- `src.retrieval.OllamaEmbedder` é um embedder de saco de palavras determinístico;
- `src.answering.answer_question` é falso na maioria dos testes (um teste usa o real,
  com o cliente falso).

O `AppTest` desta versão suporta `file_uploader.set_value(...)`, então o fluxo de upload,
processamento e invalidação é exercitado de ponta a ponta. O loader e o chunking reais
são usados com os PDFs fictícios de `docs/amostras/`. Ollama desligado, modelo ausente e
troca do modelo de embedding ficam em `test_app_local.py`.
"""

from __future__ import annotations

import inspect
import json
import re
import zlib
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import streamlit as st
from google.protobuf import text_format
from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import Expander

from src import answering, config, providers, retrieval
from src.answering import REFUSAL_TEXT, Answer, AnsweringError
from src.chunking import Chunk, chunk_pages
from src.loader import load_pdfs
from src.retrieval import RetrievalError, RetrievedChunk, VectorIndex

RAIZ = Path(__file__).resolve().parent.parent
APP = RAIZ / "app.py"
AMOSTRAS = RAIZ / "docs" / "amostras"

SETTINGS = config.Settings(model="modelo-gerador", embedding_model="modelo-vetores")
LOAD_SETTINGS_REAL = config.load_settings  # a fixture substitui config.load_settings
ANSWER_QUESTION_REAL = answering.answer_question
TIMEOUT = 30

REGULAMENTO = "regulamento_condominio.pdf"
ATA = "ata_assembleia_2026.pdf"
AVISO = "aviso_com_pagina_em_branco.pdf"
DIGITALIZADO = "digitalizado_sem_texto.pdf"

AVISO_MUDANCA = "Os documentos mudaram. Clique em Processar para reindexar."
NOTA_INVALIDAS = "O modelo citou fontes inexistentes, que foram descartadas"


# ---------------------------------------------------------------- fakes


class ClienteFalso:
    """Substitui `providers.OllamaClient(base_url, timeout)`. Registra as instâncias.

    O app cria um cliente por execução em `check_local_ready` (e o fecha) e um cliente
    para o backend, que fica no `st.cache_resource` e não é fechado. `chat` devolve JSON
    citando o primeiro `id="..."` do prompt; assim o `answer_question` real funciona sem
    rede. Embeddings pelo cliente são proibidos (o embedder é falso).
    """

    instancias: list["ClienteFalso"] = []
    instalados: set[str] = set()

    def __init__(self, base_url, timeout, transport=None):
        self.base_url = base_url
        self.timeout = timeout
        self.fechado = False
        self.prompts: list[str] = []
        ClienteFalso.instancias.append(self)

    def close(self):
        self.fechado = True

    def list_models(self):
        return set(ClienteFalso.instalados)

    def embed(self, model, texts):  # pragma: no cover - não deve ocorrer
        raise AssertionError("O teste não pode gerar embeddings pelo cliente (o embedder é falso).")

    def chat(self, model, prompt, schema, options=None, think=False):
        self.prompts.append(prompt)
        ids = re.findall(r'id="([^"]+)"', prompt)
        conteudo = {"status": "answered", "answer": "Resposta gerada pelo fake.", "citations": ids[:1]}
        return {"message": {"content": json.dumps(conteudo, ensure_ascii=False)}, "done_reason": "stop"}


def clientes_do_backend() -> list[ClienteFalso]:
    """Clientes criados pelo `build_backend` (os de `check_local_ready` são fechados)."""
    return [c for c in ClienteFalso.instancias if not c.fechado]


DIM = 64


def vetor_bow(texto: str) -> np.ndarray:
    """Saco de palavras com hashing estável (crc32) em DIM dimensões + viés (nunca zero)."""
    v = np.zeros(DIM + 1, dtype=np.float32)
    for palavra in re.findall(r"\w+", texto.lower()):
        v[zlib.crc32(palavra.encode("utf-8")) % DIM] += 1.0
    v[DIM] = 0.1
    return v


class EmbedderFalso:
    """Substitui `retrieval.OllamaEmbedder(client, model, ...)`."""

    instancias: list["EmbedderFalso"] = []
    erro_nos_documentos: BaseException | None = None

    def __init__(self, client=None, model=None, *args, **kwargs):
        self.client = client if client is not None else kwargs.get("client")
        self.model = model if model is not None else kwargs.get("model")
        self.identity = f"ollama:{self.model}"  # o app compara com index.embedder_id
        self.documentos: list[list[str]] = []
        self.consultas: list[str] = []
        EmbedderFalso.instancias.append(self)

    def embed_documents(self, texts):
        self.documentos.append(list(texts))
        if EmbedderFalso.erro_nos_documentos is not None:
            raise EmbedderFalso.erro_nos_documentos
        return np.asarray([vetor_bow(t) for t in texts], dtype=np.float32)

    def embed_query(self, text):
        self.consultas.append(text)
        return vetor_bow(text)


class AnswerQuestionFalso:
    """Substitui `answering.answer_question`. Devolve (ou levanta) os itens de `fila`,
    em ordem; sem fila, devolve `padrao`. Registra os argumentos normalizados."""

    def __init__(self, padrao: Answer):
        self.padrao = padrao
        self.fila: list[Answer | BaseException] = []
        self.chamadas: list[dict] = []

    def __call__(self, *args, **kwargs):
        ligados = inspect.signature(ANSWER_QUESTION_REAL).bind(*args, **kwargs)
        ligados.apply_defaults()
        self.chamadas.append(dict(ligados.arguments))
        item = self.fila.pop(0) if self.fila else self.padrao
        if isinstance(item, BaseException):
            raise item
        return item


# ---------------------------------------------------------------- dados de apoio


def chunk(chunk_id: str, texto: str, fonte: str = REGULAMENTO, pagina: int = 3) -> Chunk:
    return Chunk(chunk_id=chunk_id, source_name=fonte, page_number=pagina, text=texto)


C_PISCINA = chunk("S1-P3-C1", "A piscina funciona de terça a domingo, das 8h às 21h.")
C_SEGUNDA = chunk("S1-P3-C2", "A piscina fica fechada às segundas-feiras para limpeza.")
C_ATA = chunk("S2-P2-C1", "A piscina ficará fechada de 1º a 30/06/2026 para reforma.", ATA, 2)
C_VAGA = chunk("S1-P4-C1", "Cada unidade tem direito a 1 vaga de garagem.", REGULAMENTO, 4)

CONTEXTO = (
    RetrievedChunk(C_PISCINA, 0.87654),
    RetrievedChunk(C_SEGUNDA, 0.81234),
    RetrievedChunk(C_ATA, 0.70001),
    RetrievedChunk(C_VAGA, 0.12345),
)

RESPOSTA_OK = Answer(
    text="A piscina abre de terça a domingo, das 8h às 21h.",
    found=True,
    sources=CONTEXTO[:3],
    context=CONTEXTO,
    invalid_citations=(),
    refusal_reason=None,
)
RESPOSTA_RECUSA = Answer(
    text=REFUSAL_TEXT,
    found=False,
    sources=(),
    context=CONTEXTO,
    invalid_citations=(),
    refusal_reason="not_found",
)


def fonte_dict(item: RetrievedChunk) -> dict:
    c = item.chunk
    return {
        "chunk_id": c.chunk_id,
        "source_name": c.source_name,
        "page_number": c.page_number,
        "score": item.score,
        "text": c.text,
    }


def msg_usuario(texto: str) -> dict:
    return {"role": "user", "content": texto}


def msg_assistente(texto, found=True, sources=(), context=CONTEXTO, invalid=(), error=False):
    return {
        "role": "assistant",
        "content": texto,
        "found": found,
        "sources": [fonte_dict(s) for s in sources],
        "context": [fonte_dict(s) for s in context],
        "invalid_citations": list(invalid),
        "error": error,
    }


def pdf(nome: str) -> tuple[str, bytes, str]:
    return (nome, (AMOSTRAS / nome).read_bytes(), "application/pdf")


# ---------------------------------------------------------------- utilitários de UI


def nos(no, pular_expanders: bool = False):
    """Percorre a árvore de elementos a partir de `no` (inclusive)."""
    yield no
    for filho in getattr(no, "children", {}).values():
        if pular_expanders and isinstance(filho, Expander):
            continue
        yield from nos(filho, pular_expanders)


def texto_do_no(no) -> str:
    proto = getattr(no, "proto", None)
    if proto is None or not hasattr(proto, "ListFields"):
        return ""
    return text_format.MessageToString(proto, as_utf8=True)


# O app escapa Markdown (\_, \., \$...) em nomes e respostas; os testes comparam o que o
# usuário vê, então removem as barras de escape. No texto do proto a barra vem dobrada.
_ESCAPAVEIS = r"[\\`*_{}\[\]()#+\-.!|$<>~]"


def sem_escape(texto_md: str) -> str:
    texto_md = re.sub(r"\\\\(" + _ESCAPAVEIS + ")", r"\1", texto_md)
    return re.sub(r"\\(" + _ESCAPAVEIS + ")", r"\1", texto_md)


def texto(no, pular_expanders: bool = False) -> str:
    """Todo o conteúdo renderizado sob `no`, como texto (labels, corpos, placeholders)."""
    return sem_escape("\n".join(texto_do_no(n) for n in nos(no, pular_expanders)))


def texto_tela(at: AppTest) -> str:
    return texto(at._tree)


def valores(elementos) -> list[str]:
    return [sem_escape(str(e.value)) for e in elementos]


def botao(at: AppTest, rotulo: str):
    achados = [b for b in at.button if b.label == rotulo]
    assert achados, f"botão {rotulo!r} não encontrado; há {[b.label for b in at.button]}"
    return achados[0]


def uploader(at: AppTest):
    assert len(at.file_uploader) == 1, "esperado exatamente um st.file_uploader"
    return at.file_uploader[0]


def chat_desabilitado(at: AppTest) -> bool:
    assert len(at.chat_input) == 1, "esperado exatamente um st.chat_input"
    return bool(at.chat_input[0].proto.disabled)


def mensagens_chat(at: AppTest, papel: str):
    return [m for m in at.chat_message if m.name == papel]


def assert_sem_excecao(at: AppTest):
    assert not at.exception, [e.value for e in at.exception]


def processar(at: AppTest, *nomes: str) -> AppTest:
    uploader(at).set_value([pdf(n) for n in nomes]).run()
    assert_sem_excecao(at)
    botao(at, "Processar documentos").click().run()
    assert_sem_excecao(at)
    return at


def perguntar(at: AppTest, pergunta: str) -> AppTest:
    at.chat_input[0].set_value(pergunta).run()
    return at


# ---------------------------------------------------------------- fixtures


@pytest.fixture
def isolado(monkeypatch):
    """Isola o app do `.env`, do Ollama real e do cache de outros testes.

    Devolve {"settings": ...}; trocar o valor muda o que `load_settings` devolve.
    """
    monkeypatch.setattr(config, "load_dotenv", lambda *a, **k: False)
    atual = {"settings": SETTINGS}
    monkeypatch.setattr(config, "load_settings", lambda *a, **k: atual["settings"])
    ClienteFalso.instancias = []
    ClienteFalso.instalados = {SETTINGS.model, SETTINGS.embedding_model}
    EmbedderFalso.instancias = []
    EmbedderFalso.erro_nos_documentos = None
    monkeypatch.setattr(providers, "OllamaClient", ClienteFalso)
    monkeypatch.setattr(retrieval, "OllamaEmbedder", EmbedderFalso)
    st.cache_resource.clear()  # o backend é @st.cache_resource: não herdar de outro teste
    yield atual
    st.cache_resource.clear()


@pytest.fixture
def fakes(isolado, monkeypatch):
    """Substitui tudo que tocaria o Ollama ou o .env; devolve os fakes para inspeção."""
    resposta = AnswerQuestionFalso(RESPOSTA_OK)
    monkeypatch.setattr(answering, "answer_question", resposta)
    return SimpleNamespace(answer=resposta, atual=isolado)


def novo_app() -> AppTest:
    return AppTest.from_file(str(APP), default_timeout=TIMEOUT)


@pytest.fixture
def at(fakes) -> AppTest:
    app = novo_app().run()
    assert_sem_excecao(app)
    return app


@pytest.fixture
def at_indexado(at) -> AppTest:
    """App com o regulamento processado (índice real, embeddings falsos)."""
    return processar(at, REGULAMENTO)


# ---------------------------------------------------------------- inicialização / configuração


def test_config_error_mostra_erro_e_nao_mostra_chat(isolado, monkeypatch):
    mensagem = "DOCUMIND_OLLAMA_TIMEOUT deve ser um número de segundos maior que zero."

    def falha(*a, **k):
        raise config.ConfigError(mensagem)

    monkeypatch.setattr(config, "load_settings", falha)

    app = novo_app().run()

    assert_sem_excecao(app)
    assert any(mensagem in e for e in valores(app.error))
    assert ".env" in texto_tela(app)  # orienta a corrigir o .env e reiniciar
    assert len(app.chat_input) == 0
    assert len(app.chat_message) == 0
    assert ClienteFalso.instancias == []  # st.stop() antes de tocar no Ollama
    assert EmbedderFalso.instancias == []


def test_url_do_ollama_fora_da_maquina_com_load_settings_real(isolado, monkeypatch):
    """Caminho real do `load_settings`: URL remota é recusada antes de qualquer conexão."""
    monkeypatch.setattr(config, "load_settings", LOAD_SETTINGS_REAL)
    monkeypatch.setenv("DOCUMIND_OLLAMA_URL", "http://servidor.exemplo.com:11434")

    app = novo_app().run()

    assert_sem_excecao(app)
    erros = " ".join(valores(app.error))
    assert "DOCUMIND_OLLAMA_URL" in erros
    assert "esta máquina" in erros
    assert len(app.chat_input) == 0
    assert len(app.chat_message) == 0
    assert ClienteFalso.instancias == []  # nenhum cliente para o endereço remoto


def test_backend_criado_uma_vez_por_configuracao(at, fakes):
    at.run()
    at.run()
    # check_local_ready cria (e fecha) um cliente por execução; o backend, um só.
    assert len(EmbedderFalso.instancias) == 1
    assert len(clientes_do_backend()) == 1
    emb = EmbedderFalso.instancias[0]
    assert emb.client is clientes_do_backend()[0]
    assert emb.model == SETTINGS.embedding_model
    assert all(c.base_url == SETTINGS.ollama_url for c in ClienteFalso.instancias)
    assert all(c.timeout == SETTINGS.timeout for c in ClienteFalso.instancias)

    # Outra configuração → outro backend (a chave do cache é a Settings).
    outra = config.Settings(model=SETTINGS.model, embedding_model="outro-vetores")
    ClienteFalso.instalados = {outra.model, outra.embedding_model}
    fakes.atual["settings"] = outra
    at.run()
    assert_sem_excecao(at)
    assert [e.model for e in EmbedderFalso.instancias] == [SETTINGS.embedding_model, "outro-vetores"]


def test_todo_cliente_aponta_para_o_ollama_local_em_todo_o_fluxo(at, fakes):
    processar(at, REGULAMENTO)
    perguntar(at, "Qual o horário da piscina?")
    fakes.answer.fila.append(AnsweringError("Falha controlada do modelo."))
    perguntar(at, "E às segundas?")
    assert_sem_excecao(at)
    assert ClienteFalso.instancias
    assert {c.base_url for c in ClienteFalso.instancias} == {config.DEFAULT_OLLAMA_URL}


# ---------------------------------------------------------------- estado inicial


def test_estado_inicial_sem_indice(at):
    assert len(at.title) >= 1
    assert at.info, "sem índice deve haver um st.info pedindo para enviar/processar"
    assert chat_desabilitado(at)
    assert botao(at, "Processar documentos").disabled
    assert at.session_state["messages"] == []
    assert at.session_state["index"] is None


def test_uploader_na_barra_lateral_com_limites_visiveis(at):
    up = at.sidebar.file_uploader
    assert len(up) == 1
    assert up[0].label == "Envie de 1 a 3 PDFs"
    assert up[0].accept_multiple_files
    assert any("pdf" in t.lower() for t in up[0].allowed_type)
    lateral = texto(at.sidebar)
    assert "10 MB" in lateral
    assert "100 páginas" in lateral
    assert "OCR" in lateral
    rotulos = [b.label for b in at.sidebar.button]
    assert "Processar documentos" in rotulos
    assert "Limpar conversa" in rotulos


def test_aviso_de_privacidade(at):
    tela = texto_tela(at)
    lateral = texto(at.sidebar)
    assert providers.PRIVACY_NOTE in lateral
    assert "não são enviados para a internet" in tela
    assert "Ollama local" in lateral
    assert SETTINGS.model in lateral and SETTINGS.embedding_model in lateral


def test_processar_habilita_com_arquivos(at):
    uploader(at).set_value([pdf(REGULAMENTO)]).run()
    assert not botao(at, "Processar documentos").disabled
    # enviar sem processar não cria índice nem mostra aviso de mudança
    assert at.session_state["index"] is None
    assert chat_desabilitado(at)
    assert AVISO_MUDANCA not in valores(at.info)


# ---------------------------------------------------------------- processamento


def test_processar_sucesso(at, fakes):
    at.session_state["messages"] = [msg_usuario("velha"), msg_assistente("velha")]
    processar(at, REGULAMENTO, ATA)

    carregado = load_pdfs([(n, (AMOSTRAS / n).read_bytes()) for n in (REGULAMENTO, ATA)])
    n_trechos = len(chunk_pages(carregado.pages))

    sucesso = " ".join(valores(at.success))
    assert re.search(r"\b2\b", sucesso)
    assert re.search(rf"\b{n_trechos}\b", sucesso)

    indice = at.session_state["index"]
    assert isinstance(indice, VectorIndex)
    assert len(indice.chunks) == n_trechos
    assert at.session_state["messages"] == []
    assert at.session_state["documents"]
    hashes = {n: sha256((AMOSTRAS / n).read_bytes()).hexdigest() for n in (REGULAMENTO, ATA)}
    assert tuple(at.session_state["fingerprint"]) == tuple(sorted(hashes.items()))

    # embedder criado com o cliente do backend (cacheado) e o modelo de embedding das settings
    assert EmbedderFalso.instancias
    emb = EmbedderFalso.instancias[-1]
    assert emb.client is clientes_do_backend()[0]
    assert emb.model == SETTINGS.embedding_model
    assert sum(len(d) for d in emb.documentos) == n_trechos

    lateral = texto(at.sidebar)
    assert REGULAMENTO in lateral and ATA in lateral
    assert not chat_desabilitado(at)


def test_lista_de_documentos_mostra_paginas_com_texto_e_trechos(at):
    processar(at, AVISO)
    carregado = load_pdfs([(AVISO, (AMOSTRAS / AVISO).read_bytes())])
    n_trechos = len(chunk_pages(carregado.pages))
    lateral = texto(at.sidebar)
    assert AVISO in lateral
    assert re.search(r"2\s*(/|de)\s*3", lateral), "páginas com texto sobre o total"
    assert re.search(rf"\b{n_trechos}\b", lateral)


def test_pagina_vazia_vira_warning(at):
    processar(at, AVISO)
    avisos = " ".join(valores(at.warning))
    assert AVISO in avisos
    assert isinstance(at.session_state["index"], VectorIndex)


def test_pdf_sem_texto_vira_erro_e_nao_indexa(at):
    processar(at, DIGITALIZADO)
    assert any(DIGITALIZADO in e for e in valores(at.error))
    assert at.session_state["index"] is None
    assert not at.success
    assert chat_desabilitado(at)


def test_erro_de_um_arquivo_nao_impede_os_outros(at):
    processar(at, REGULAMENTO, DIGITALIZADO)
    assert any(DIGITALIZADO in e for e in valores(at.error))
    indice = at.session_state["index"]
    assert isinstance(indice, VectorIndex)
    assert {c.source_name for c in indice.chunks} == {REGULAMENTO}


def test_erro_do_conjunto_vira_erro(at):
    # quatro arquivos: PdfLoadError do conjunto (limite de 3)
    arquivos = [pdf(REGULAMENTO), pdf(ATA), pdf(AVISO), pdf(DIGITALIZADO)]
    uploader(at).set_value(arquivos).run()
    botao(at, "Processar documentos").click().run()
    assert_sem_excecao(at)
    assert any("3" in e for e in valores(at.error))
    assert at.session_state["index"] is None
    assert not at.success


def test_retrieval_error_na_indexacao_vira_erro(at):
    EmbedderFalso.erro_nos_documentos = RetrievalError("O Ollama não respondeu aos embeddings.")
    processar(at, REGULAMENTO)
    assert "O Ollama não respondeu aos embeddings." in valores(at.error)
    assert at.session_state["index"] is None
    assert not at.success
    assert chat_desabilitado(at)


# ---------------------------------------------------------------- invalidação


def test_mudanca_de_arquivos_invalida_indice_e_historico(at_indexado):
    at = at_indexado
    perguntar(at, "Qual o horário da piscina?")
    assert at.session_state["messages"]

    uploader(at).set_value([pdf(REGULAMENTO), pdf(ATA)]).run()

    assert_sem_excecao(at)
    assert AVISO_MUDANCA in valores(at.info)
    assert at.session_state["index"] is None
    assert not at.session_state["documents"]
    assert at.session_state["messages"] == []
    assert len(at.chat_message) == 0
    assert chat_desabilitado(at)


def test_remover_todos_os_arquivos_invalida(at_indexado):
    at = at_indexado
    uploader(at).clear().run()
    assert_sem_excecao(at)
    assert at.session_state["index"] is None
    assert at.session_state["messages"] == []
    assert chat_desabilitado(at)
    assert botao(at, "Processar documentos").disabled


def test_reenviar_mesmos_arquivos_nao_invalida(at_indexado):
    at = at_indexado
    indice = at.session_state["index"]
    uploader(at).set_value([pdf(REGULAMENTO)]).run()  # mesmo nome e tamanho, novo file_id
    assert at.session_state["index"] is indice
    assert AVISO_MUDANCA not in valores(at.info)


def test_substituir_pdf_de_mesmo_nome_e_tamanho_invalida(at_indexado):
    at = at_indexado
    original = (AMOSTRAS / REGULAMENTO).read_bytes()
    diferente = bytes([original[0] ^ 1]) + original[1:]
    assert len(diferente) == len(original)

    uploader(at).set_value([(REGULAMENTO, diferente, "application/pdf")]).run()

    assert_sem_excecao(at)
    assert AVISO_MUDANCA in valores(at.info)
    assert at.session_state["index"] is None
    assert at.session_state["messages"] == []
    assert chat_desabilitado(at)


def test_reprocessar_novo_conjunto_reindexa(at_indexado):
    at = at_indexado
    processar(at, ATA)
    indice = at.session_state["index"]
    assert isinstance(indice, VectorIndex)
    assert {c.source_name for c in indice.chunks} == {ATA}
    assert not chat_desabilitado(at)


# ---------------------------------------------------------------- perguntas


def test_pergunta_gera_resposta_e_passa_argumentos(at_indexado, fakes):
    at = at_indexado
    perguntar(at, "Qual o horário da piscina?")
    assert_sem_excecao(at)

    assert len(fakes.answer.chamadas) == 1
    chamada = fakes.answer.chamadas[0]
    assert chamada["question"] == "Qual o horário da piscina?"
    assert chamada["index"] is at.session_state["index"]
    gerador = chamada["generator"]
    assert isinstance(gerador, answering.OllamaGenerator)
    assert gerador._client is clientes_do_backend()[0]
    assert gerador._model == SETTINGS.model
    assert gerador._think == SETTINGS.think
    assert isinstance(chamada["embedder"], EmbedderFalso)
    assert chamada["embedder"].model == SETTINGS.embedding_model
    assert chamada["previous_question"] is None

    msgs = at.session_state["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content"] == "Qual o horário da piscina?"
    resp = msgs[1]
    assert resp["content"] == RESPOSTA_OK.text
    assert resp["found"] is True
    assert resp["error"] is False
    assert list(resp["invalid_citations"]) == []
    assert [s["chunk_id"] for s in resp["sources"]] == [s.chunk.chunk_id for s in RESPOSTA_OK.sources]
    assert [c["chunk_id"] for c in resp["context"]] == [c.chunk.chunk_id for c in CONTEXTO]
    primeira = resp["sources"][0]
    for k in ("chunk_id", "source_name", "page_number", "text"):
        assert primeira[k] == fonte_dict(CONTEXTO[0])[k], k
    assert primeira["score"] == pytest.approx(CONTEXTO[0].score)

    assert [m.name for m in at.chat_message] == ["user", "assistant"]
    assert RESPOSTA_OK.text in texto(mensagens_chat(at, "assistant")[0])


def test_segunda_pergunta_recebe_previous_question(at_indexado, fakes):
    at = at_indexado
    perguntar(at, "Qual o horário da piscina?")
    perguntar(at, "E às segundas?")
    assert_sem_excecao(at)
    assert [c["previous_question"] for c in fakes.answer.chamadas] == [
        None,
        "Qual o horário da piscina?",
    ]
    assert fakes.answer.chamadas[1]["question"] == "E às segundas?"
    assert len(at.session_state["messages"]) == 4
    assert [m.name for m in at.chat_message] == ["user", "assistant", "user", "assistant"]


def test_answering_error_vira_mensagem_de_erro_sem_resposta_falsa(at_indexado, fakes):
    at = at_indexado
    fakes.answer.fila.append(AnsweringError("O modelo não respondeu; tente de novo."))
    perguntar(at, "Qual o horário da piscina?")
    assert_sem_excecao(at)

    ultima = at.session_state["messages"][-1]
    assert ultima["role"] == "assistant"
    assert ultima["error"] is True
    assert "O modelo não respondeu; tente de novo." in ultima["content"]
    assert not ultima.get("sources")

    assistente = mensagens_chat(at, "assistant")[-1]
    assert any("O modelo não respondeu" in str(e.value) for e in assistente.error)
    assert "Fontes" not in texto(assistente)
    assert RESPOSTA_OK.text not in texto_tela(at)


def test_retrieval_error_na_pergunta_vira_mensagem_de_erro(at_indexado, fakes):
    at = at_indexado
    fakes.answer.fila.append(RetrievalError("O Ollama está instável no momento."))
    perguntar(at, "Qual o horário da piscina?")
    assert_sem_excecao(at)
    assert at.session_state["messages"][-1]["error"] is True
    assert any("instável" in e for e in valores(at.error))


def test_erro_inesperado_nao_e_capturado(at_indexado, fakes):
    at = at_indexado
    fakes.answer.fila.append(RuntimeError("bug de programação"))
    perguntar(at, "Qual o horário da piscina?")
    assert at.exception, "exceções fora de RetrievalError/AnsweringError devem aparecer"


def test_limpar_conversa_mantem_indice(at_indexado):
    at = at_indexado
    perguntar(at, "Qual o horário da piscina?")
    # Sem rerun extra de propósito: logo após a resposta, o usuário precisa conseguir
    # clicar em "Limpar conversa" (o AppTest recusa clique em botão desabilitado).
    indice = at.session_state["index"]
    botao(at, "Limpar conversa").click().run()
    assert_sem_excecao(at)
    assert at.session_state["messages"] == []
    assert at.session_state["index"] is indice
    assert len(at.chat_message) == 0
    assert not chat_desabilitado(at)


def test_fluxo_com_answer_question_real_e_cliente_falso(at_indexado, monkeypatch):
    """Integração da UI com o `answer_question` real: só o Ollama e o embedder são falsos."""
    monkeypatch.setattr(answering, "answer_question", ANSWER_QUESTION_REAL)
    at = at_indexado
    perguntar(at, "Qual o horário da piscina às segundas?")
    assert_sem_excecao(at)

    resp = at.session_state["messages"][-1]
    assert resp["found"] is True, resp
    assert resp["content"] == "Resposta gerada pelo fake."
    fonte = resp["sources"][0]
    assert fonte["source_name"] == REGULAMENTO
    assert re.fullmatch(r"S\d+-P\d+-C\d+", fonte["chunk_id"])
    assert f"{REGULAMENTO} — p. {fonte['page_number']}" in texto(
        mensagens_chat(at, "assistant")[-1], pular_expanders=True
    )
    assert clientes_do_backend()[0].prompts  # o modelo (falso) foi chamado pelo backend


# ---------------------------------------------------------------- exibição do histórico


def renderizar_historico(at: AppTest, mensagens: list[dict]) -> AppTest:
    at.session_state["messages"] = mensagens
    at.run()
    assert_sem_excecao(at)
    return at


def test_historico_resposta_com_fontes_sem_repetir_par(at_indexado):
    at = renderizar_historico(
        at_indexado,
        [msg_usuario("Horário da piscina?"), msg_assistente(RESPOSTA_OK.text, sources=CONTEXTO[:3])],
    )
    assert [m.name for m in at.chat_message] == ["user", "assistant"]
    assistente = mensagens_chat(at, "assistant")[0]
    fora = texto(assistente, pular_expanders=True)

    assert RESPOSTA_OK.text in fora
    assert "Fontes" in fora
    # duas fontes na p. 3 do regulamento → o par aparece uma vez só
    assert fora.count(f"{REGULAMENTO} — p. 3") == 1
    assert fora.count(f"{ATA} — p. 2") == 1
    # a p. 4 só está no contexto, não é fonte
    assert f"{REGULAMENTO} — p. 4" not in fora
    assert not assistente.warning


def test_historico_cada_fonte_tem_expander_com_trecho(at_indexado):
    at = renderizar_historico(
        at_indexado,
        [msg_usuario("Horário?"), msg_assistente(RESPOSTA_OK.text, sources=CONTEXTO[:3])],
    )
    assistente = mensagens_chat(at, "assistant")[0]
    expanders = [e for e in assistente.expander if e.label != "Trechos consultados"]
    conteudo = "\n".join(texto(e) for e in expanders)
    for item in CONTEXTO[:3]:
        assert item.chunk.text in conteudo
        assert item.chunk.chunk_id in conteudo


def test_historico_trechos_consultados_com_score_3_casas(at_indexado):
    at = renderizar_historico(
        at_indexado,
        [msg_usuario("Horário?"), msg_assistente(RESPOSTA_OK.text, sources=CONTEXTO[:1])],
    )
    assistente = mensagens_chat(at, "assistant")[0]
    trechos = [e for e in assistente.expander if e.label == "Trechos consultados"]
    assert len(trechos) == 1
    conteudo = texto(trechos[0])
    for item in CONTEXTO:
        assert item.chunk.chunk_id in conteudo
        assert item.chunk.source_name in conteudo
        assert str(item.chunk.page_number) in conteudo
    for score in ("0.877", "0.812", "0.700", "0.123"):
        assert score in conteudo or score.replace(".", ",") in conteudo, score


def test_historico_recusa_em_warning_com_trechos_consultados(at_indexado):
    at = renderizar_historico(
        at_indexado,
        [msg_usuario("CNPJ?"), msg_assistente(REFUSAL_TEXT, found=False, sources=())],
    )
    assistente = mensagens_chat(at, "assistant")[0]
    assert any(REFUSAL_TEXT in str(w.value) for w in assistente.warning)
    assert "Fontes" not in texto(assistente, pular_expanders=True)
    assert [e.label for e in assistente.expander].count("Trechos consultados") == 1


def test_historico_nota_de_citacoes_invalidas(at_indexado):
    at = renderizar_historico(
        at_indexado,
        [
            msg_usuario("Horário?"),
            msg_assistente(RESPOSTA_OK.text, sources=CONTEXTO[:1], invalid=("S9-P99-C9",)),
        ],
    )
    fora = texto(mensagens_chat(at, "assistant")[0], pular_expanders=True)
    assert NOTA_INVALIDAS in fora
    assert "S9-P99-C9" in fora


def test_historico_sem_citacoes_invalidas_nao_mostra_nota(at_indexado):
    at = renderizar_historico(
        at_indexado,
        [msg_usuario("Horário?"), msg_assistente(RESPOSTA_OK.text, sources=CONTEXTO[:1])],
    )
    assert NOTA_INVALIDAS not in texto_tela(at)


def test_historico_erro_em_st_error(at_indexado):
    at = renderizar_historico(
        at_indexado,
        [
            msg_usuario("Horário?"),
            msg_assistente("O Ollama não respondeu a tempo.", found=False, sources=(), context=(), error=True),
        ],
    )
    assistente = mensagens_chat(at, "assistant")[0]
    assert any("O Ollama não respondeu a tempo." in str(e.value) for e in assistente.error)
    assert "Fontes" not in texto(assistente, pular_expanders=True)


def test_historico_misto_renderiza_na_ordem(at_indexado):
    at = renderizar_historico(
        at_indexado,
        [
            msg_usuario("P1"),
            msg_assistente(RESPOSTA_OK.text, sources=CONTEXTO[:1]),
            msg_usuario("P2"),
            msg_assistente(REFUSAL_TEXT, found=False, sources=()),
            msg_usuario("P3"),
            msg_assistente("Falhou.", found=False, sources=(), context=(), error=True),
        ],
    )
    assert [m.name for m in at.chat_message] == ["user", "assistant"] * 3
    usuarios = [texto(m) for m in mensagens_chat(at, "user")]
    for i, pergunta in enumerate(("P1", "P2", "P3")):
        assert pergunta in usuarios[i]
    assistentes = mensagens_chat(at, "assistant")
    assert not assistentes[0].warning and not assistentes[0].error
    assert assistentes[1].warning
    assert assistentes[2].error


# ---------------------------------------------------------------- lacunas apontadas na revisão (mutação)


def markdowns_brutos(no) -> list[str]:
    """Corpo dos st.markdown como enviado ao navegador, com os escapes."""
    return [n.proto.body for n in nos(no) if type(n).__name__ == "Markdown"]


def test_terceira_pergunta_recebe_a_segunda_como_anterior(at_indexado, fakes):
    at = at_indexado
    for pergunta in ("Primeira?", "Segunda?", "Terceira?"):
        perguntar(at, pergunta)
    assert [c["previous_question"] for c in fakes.answer.chamadas] == [None, "Primeira?", "Segunda?"]


def test_resposta_com_imagem_e_link_nao_vira_markdown_ativo(at_indexado):
    maliciosa = "Veja ![p](https://evil.example/px?q=1) e [aqui](https://evil.example)."
    at = renderizar_historico(
        at_indexado, [msg_usuario("x?"), msg_assistente(maliciosa, sources=CONTEXTO[:1])]
    )
    corpo = " ".join(markdowns_brutos(mensagens_chat(at, "assistant")[0]))
    # Imagem/link só funcionam com "![", "[" e "](" sem barra de escape antes.
    assert not re.search(r"(?<!\\)!(?<!\\)\[", corpo)
    assert not re.search(r"(?<!\\)\]\(", corpo)
    assert r"\!\[p\]" in corpo


def test_cifrao_da_resposta_e_escapado(at_indexado):
    at = renderizar_historico(
        at_indexado, [msg_usuario("x?"), msg_assistente("Salão R$ 150 e churrasqueira R$ 80.",
                                                          sources=CONTEXTO[:1])]
    )
    corpo = " ".join(markdowns_brutos(mensagens_chat(at, "assistant")[0]))
    assert r"R\$ 150" in corpo and r"R\$ 80" in corpo


def test_nome_de_arquivo_com_markdown_e_escapado_nas_fontes(at_indexado):
    nome = "[clique](https://evil.example)_x_.pdf"
    fonte = RetrievedChunk(chunk("S1-P1-C1", "texto", fonte=nome, pagina=1), 0.9)
    at = renderizar_historico(
        at_indexado, [msg_usuario("x?"), msg_assistente("ok", sources=(fonte,), context=(fonte,))]
    )
    corpo = " ".join(markdowns_brutos(mensagens_chat(at, "assistant")[0]))
    assert not re.search(r"(?<!\\)\]\(", corpo)
    assert nome in texto(mensagens_chat(at, "assistant")[0])  # o usuário vê o nome literal


def test_nenhum_markdown_permite_html(at_indexado):
    at = renderizar_historico(
        at_indexado, [msg_usuario("<b>x</b>?"), msg_assistente("<script>x</script>", sources=CONTEXTO[:1])]
    )
    assert not any(n.proto.allow_html for n in nos(at._tree) if type(n).__name__ == "Markdown")


def test_trecho_do_pdf_e_mostrado_como_texto_literal(at_indexado):
    at = renderizar_historico(
        at_indexado, [msg_usuario("x?"), msg_assistente("ok", sources=CONTEXTO[:1])]
    )
    literais = [n.value for n in nos(mensagens_chat(at, "assistant")[0]) if type(n).__name__ == "Text"]
    assert C_PISCINA.text in literais

