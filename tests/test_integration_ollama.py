"""Teste real opcional contra o Ollama instalado nesta máquina (modo local padrão).

É pulado quando o Ollama não responde em DOCUMIND_OLLAMA_URL (padrão 127.0.0.1:11434) ou
quando falta um dos modelos configurados. Não usa chave nem internet.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from src.answering import answer_question
from src.chunking import chunk_pages
from src.config import load_settings
from src.loader import load_pdfs
from src.ollama_client import OllamaClient, OllamaError, missing_models
from src.providers import build_backend
from src.retrieval import build_index

AMOSTRAS = Path(__file__).resolve().parent.parent / "docs" / "amostras"

# Só variáveis do modo local; ignora DOCUMIND_PROVIDER e a chave do Gemini.
_ENV = {k: v for k, v in os.environ.items() if k.startswith(("OLLAMA_", "DOCUMIND_OLLAMA"))}
SETTINGS = load_settings(env=_ENV)


def _motivo_para_pular() -> str | None:
    try:
        with OllamaClient(SETTINGS.ollama_url, 5) as cliente:
            faltando = missing_models(cliente, [SETTINGS.model, SETTINGS.embedding_model])
    except OllamaError:
        return f"Ollama não responde em {SETTINGS.ollama_url}"
    return f"modelos ausentes: {faltando}" if faltando else None


_MOTIVO = _motivo_para_pular()
pytestmark = pytest.mark.skipif(_MOTIVO is not None, reason=_MOTIVO or "")


@pytest.fixture(scope="module")
def pipeline():
    with OllamaClient(SETTINGS.ollama_url, SETTINGS.timeout) as cliente:
        backend = build_backend(SETTINGS, ollama_client=cliente)
        nomes = ("regulamento_condominio.pdf", "ata_assembleia_2026.pdf")
        resultado = load_pdfs([(n, (AMOSTRAS / n).read_bytes()) for n in nomes])
        indice = build_index(chunk_pages(resultado.pages), backend.embedder)
        yield backend, indice


def test_embeddings_locais_tem_formato_e_valores_validos(pipeline):
    backend, indice = pipeline
    assert indice.embedder_id == f"ollama:{SETTINGS.embedding_model}"
    assert indice.matrix.shape[0] == len(indice.chunks) and indice.matrix.shape[1] >= 64
    vetor = backend.embedder.embed_query("Qual o horário da piscina?")
    assert vetor.shape == (indice.matrix.shape[1],) and np.isfinite(vetor).all()


def test_resposta_local_cita_a_pagina_certa(pipeline):
    backend, indice = pipeline
    answer = answer_question("Qual a taxa de reserva da churrasqueira?", indice,
                             backend.embedder, backend.generator)
    assert answer.found
    assert "80" in answer.text
    assert ("regulamento_condominio.pdf", 3) in {(s.chunk.source_name, s.chunk.page_number) for s in answer.sources}


def test_pergunta_sem_base_e_recusada_localmente(pipeline):
    backend, indice = pipeline
    answer = answer_question("Qual é o CNPJ do condomínio?", indice, backend.embedder, backend.generator)
    assert not answer.found
    assert answer.sources == ()


def test_fluxo_local_completo_sem_acesso_a_internet(monkeypatch):
    """Bloqueia qualquer conexão fora de 127.0.0.1/::1 e roda o fluxo inteiro de novo.

    É o equivalente automatizado de "desligar a internet": se algum passo tentasse sair da
    máquina (Gemini, download de modelo, telemetria), a conexão falharia e o teste também.
    """
    import socket

    conectar_original = socket.socket.connect
    destinos: list = []

    def conectar_so_local(self, endereco):
        destinos.append(endereco)
        host = endereco[0] if isinstance(endereco, tuple) else endereco
        if host not in ("127.0.0.1", "::1", "localhost"):
            raise OSError(f"conexão externa bloqueada no teste: {host}")
        return conectar_original(self, endereco)

    monkeypatch.setattr(socket.socket, "connect", conectar_so_local)

    with OllamaClient(SETTINGS.ollama_url, SETTINGS.timeout) as cliente:
        backend = build_backend(SETTINGS, ollama_client=cliente)
        nomes = ("regulamento_condominio.pdf", "ata_assembleia_2026.pdf")
        resultado = load_pdfs([(n, (AMOSTRAS / n).read_bytes()) for n in nomes])
        indice = build_index(chunk_pages(resultado.pages), backend.embedder)
        answer = answer_question("Quantas vagas de garagem cada unidade tem?", indice,
                                 backend.embedder, backend.generator)
    assert answer.found and "1" in answer.text
    assert destinos  # houve conexões, e todas foram locais
    assert all(d[0] in ("127.0.0.1", "::1") for d in destinos)


def test_app_real_no_modo_local_sem_fakes():
    """Processo limpo: app.py com load_settings real (.env incluso), Ollama real, 2 PDFs.

    Sem DOCUMIND_PROVIDER, o app tem de usar o Ollama mesmo que exista GEMINI_API_KEY no
    .env, e o SDK do Gemini não pode ser carregado.
    """
    import json
    import subprocess
    import sys

    raiz = Path(__file__).resolve().parent.parent
    script = f"""
import json, sys, time
from streamlit.testing.v1 import AppTest
at = AppTest.from_file({str(raiz / 'app.py')!r}, default_timeout=300).run()
assert not at.exception and not at.error, [e.value for e in at.error]
nomes = ("regulamento_condominio.pdf", "ata_assembleia_2026.pdf")
arquivos = [(n, open({str(AMOSTRAS)!r} + "/" + n, "rb").read(), "application/pdf") for n in nomes]
at.sidebar.file_uploader[0].set_value(arquivos).run()
next(b for b in at.sidebar.button if b.label == "Processar documentos").click().run()
t = time.perf_counter()
at.chat_input[0].set_value("Qual é o valor da multa na primeira reincidência depois de maio de 2026?").run()
t_c1 = time.perf_counter() - t
at.chat_input[0].set_value("Qual é o CNPJ do condomínio?").run()
m = at.session_state["messages"]
print(json.dumps({{
    "captions": [c.value for c in at.sidebar.caption],
    "c1": m[1]["content"], "c1_fontes": [[s["source_name"], s["page_number"]] for s in m[1]["sources"]],
    "s1_found": m[3]["found"], "s1": m[3]["content"], "t_c1": round(t_c1, 1),
    "genai": any(k == "google.genai" or k.startswith("google.genai.") for k in sys.modules),
}}, ensure_ascii=False))
"""
    env = {k: v for k, v in os.environ.items() if k != "DOCUMIND_PROVIDER"}
    env["PYTHONIOENCODING"] = "utf-8"  # o console do Windows (cp1252) não imprime o emoji 🔒
    saida = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                           cwd=raiz, env=env, timeout=600, encoding="utf-8")
    assert saida.returncode == 0, saida.stderr[-2000:]
    dados = json.loads(saida.stdout.strip().splitlines()[-1])
    assert any("Ollama local" in c for c in dados["captions"])
    assert "680" in dados["c1"]
    assert ["regulamento_condominio.pdf", 6] in dados["c1_fontes"]
    assert dados["s1_found"] is False
    assert dados["genai"] is False
    print(dados)  # visível com pytest -s: resposta, fontes e tempo
