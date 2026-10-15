"""Testes do app no modo local (Ollama), com `AppTest` e um Ollama falso.

`providers.OllamaClient` é trocado por `OllamaFalsoApp`; loader, chunking, busca,
`answer_question`, parser e validação de citações são os reais.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from src import config, providers
from src.ollama_client import OllamaError

RAIZ = Path(__file__).resolve().parent.parent
APP = RAIZ / "app.py"
AMOSTRAS = RAIZ / "docs" / "amostras"
REGULAMENTO = "regulamento_condominio.pdf"
ATA = "ata_assembleia_2026.pdf"
TIMEOUT = 30


LOAD_SETTINGS_REAL = config.load_settings  # a fixture substitui config.load_settings


def settings_local(**env) -> config.Settings:
    return LOAD_SETTINGS_REAL(env={"OLLAMA_MODEL": "gen:8b", "OLLAMA_EMBEDDING_MODEL": "emb:0.6b", **env})


class OllamaFalsoApp:
    """Substitui OllamaClient(url, timeout). O comportamento vem de atributos de classe."""

    instalados = {"gen:8b", "emb:0.6b"}
    desligado = False
    instancias: list["OllamaFalsoApp"] = []
    embeds: list[tuple[str, int]] = []
    prompts: list[str] = []

    def __init__(self, base_url, timeout, transport=None):
        assert base_url.startswith("http://127.0.0.1")
        OllamaFalsoApp.instancias.append(self)

    def close(self):
        pass

    def _checar(self):
        if OllamaFalsoApp.desligado:
            raise OllamaError("Não foi possível conectar ao Ollama em http://127.0.0.1:11434.")

    def list_models(self):
        self._checar()
        return set(OllamaFalsoApp.instalados)

    def embed(self, model, texts):
        self._checar()
        OllamaFalsoApp.embeds.append((model, len(texts)))
        vetores = []
        for texto in texts:
            palavras = re.findall(r"\w+", texto.lower())
            vetores.append([float("piscina" in palavras), float("taxa" in palavras), 0.1 + len(palavras) % 5])
        return vetores

    def chat(self, model, prompt, schema, options=None, think=False):
        self._checar()
        OllamaFalsoApp.prompts.append(prompt)
        primeiro_id = re.findall(r'<trecho id="([^"]+)"', prompt)[:1]
        conteudo = {"status": "answered", "answer": "Resposta local de teste.", "citations": primeiro_id}
        return {"message": {"content": json.dumps(conteudo)}, "done_reason": "stop"}


@pytest.fixture
def local(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda *a, **k: False)
    atual = {"settings": settings_local()}
    monkeypatch.setattr(config, "load_settings", lambda *a, **k: atual["settings"])
    monkeypatch.setattr(providers, "OllamaClient", OllamaFalsoApp)
    OllamaFalsoApp.instalados = {"gen:8b", "emb:0.6b"}
    OllamaFalsoApp.desligado = False
    OllamaFalsoApp.instancias, OllamaFalsoApp.embeds, OllamaFalsoApp.prompts = [], [], []
    st.cache_resource.clear()
    yield atual
    st.cache_resource.clear()


def novo_app() -> AppTest:
    app = AppTest.from_file(str(APP), default_timeout=TIMEOUT).run()
    assert not app.exception, app.exception
    return app


def texto(app: AppTest) -> str:
    partes = [str(e.value) for grupo in (app.markdown, app.caption, app.error, app.info,
                                          app.warning, app.success) for e in grupo]
    return re.sub(r"\\(.)", r"\1", "\n".join(partes))  # tira os escapes de Markdown


def processar(app: AppTest, *nomes: str) -> AppTest:
    arquivos = [(n, (AMOSTRAS / n).read_bytes(), "application/pdf") for n in nomes]
    app.sidebar.file_uploader[0].set_value(arquivos).run()
    botao = next(b for b in app.sidebar.button if b.label == "Processar documentos")
    botao.click().run()
    assert not app.exception, app.exception
    return app


def test_sem_chave_o_app_inicia_no_modo_local(local):
    app = novo_app()
    tela = texto(app)
    assert not app.error
    assert "Ollama local" in tela and "gen:8b" in tela and "emb:0.6b" in tela
    assert "não são enviados para a internet" in tela
    assert len(app.chat_input) == 1


def test_load_settings_real_sem_env_escolhe_o_modo_local(monkeypatch):
    """Sem .env e sem variáveis: o app sobe no modo local, sem pedir chave."""
    for nome in ("OLLAMA_MODEL", "OLLAMA_EMBEDDING_MODEL", "DOCUMIND_OLLAMA_URL"):
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setattr(config, "load_dotenv", lambda *a, **k: False)
    monkeypatch.setattr(providers, "OllamaClient", OllamaFalsoApp)
    OllamaFalsoApp.desligado = False
    OllamaFalsoApp.instalados = {config.DEFAULT_OLLAMA_MODEL, config.DEFAULT_OLLAMA_EMBEDDING_MODEL}
    st.cache_resource.clear()
    app = novo_app()
    assert not app.error
    assert config.DEFAULT_OLLAMA_MODEL in texto(app)
    st.cache_resource.clear()


def test_fluxo_local_com_dois_pdfs_mostra_arquivo_pagina_e_trecho(local):
    app = processar(novo_app(), REGULAMENTO, ATA)
    assert any("2 documento(s)" in s.value for s in app.success)
    # Documentos indexados com o modelo de embedding local, sem prefixo de pergunta.
    assert {modelo for modelo, _ in OllamaFalsoApp.embeds} == {"emb:0.6b"}

    app.chat_input[0].set_value("Qual o horário da piscina?").run()
    assert not app.exception
    resposta = app.session_state["messages"][-1]
    assert resposta["found"] is True
    assert resposta["content"] == "Resposta local de teste."
    fonte = resposta["sources"][0]
    assert fonte["source_name"] in (REGULAMENTO, ATA) and fonte["page_number"] >= 1
    assert fonte["text"]  # o trecho de apoio vai junto
    tela = texto(app)
    assert f"{fonte['source_name']} — p. {fonte['page_number']}" in tela
    assert OllamaFalsoApp.prompts  # a geração foi feita pelo Ollama falso


def test_ollama_desligado_mostra_instrucao_e_para(local):
    OllamaFalsoApp.desligado = True
    app = novo_app()
    erros = re.sub(r"\\(.)", r"\1", " ".join(e.value for e in app.error))  # sem escapes de Markdown
    assert "Não foi possível conectar ao Ollama" in erros
    assert len(app.chat_input) == 0
    assert "README" in texto(app)


def test_modelo_ausente_mostra_o_comando_de_pull(local):
    OllamaFalsoApp.instalados = {"gen:8b"}
    app = novo_app()
    erros = re.sub(r"\\(.)", r"\1", " ".join(e.value for e in app.error))  # sem escapes de Markdown
    assert "ollama pull emb:0.6b" in erros
    assert len(app.chat_input) == 0


def test_troca_do_modelo_de_embedding_invalida_indice_e_conversa(local):
    app = processar(novo_app(), REGULAMENTO)
    app.chat_input[0].set_value("Qual a taxa?").run()
    assert app.session_state["index"] is not None
    assert app.session_state["messages"]

    OllamaFalsoApp.instalados = {"gen:8b", "emb:0.6b", "outro-emb"}
    local["settings"] = settings_local(OLLAMA_EMBEDDING_MODEL="outro-emb")
    app.run()
    assert not app.exception
    assert app.session_state["index"] is None
    assert app.session_state["messages"] == []
    assert any("modelo de embedding mudou" in i.value for i in app.info)


def test_ollama_cai_durante_a_pergunta_vira_erro_controlado(local):
    app = processar(novo_app(), REGULAMENTO)
    OllamaFalsoApp.desligado = True
    # A checagem de início também falharia; simula a queda só na chamada da pergunta.
    local_check = providers.check_local_ready
    try:
        providers.check_local_ready = lambda *a, **k: None
        app.chat_input[0].set_value("Qual a taxa?").run()
    finally:
        providers.check_local_ready = local_check
    assert not app.exception
    ultima = app.session_state["messages"][-1]
    assert ultima["error"] is True
    assert "Ollama" in ultima["content"]
