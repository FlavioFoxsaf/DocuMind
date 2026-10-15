"""Testes de caixa-preta do `src/retrieval.py`, escritos a partir de
`docs/contratos/retrieval.md` e de `docs/contratos/chunking.md` (apenas o `Chunk`).

Nada usa rede: o cliente do Ollama e os embedders são falsos e determinísticos. O que
`tests/test_local_backend.py` já cobre do `OllamaEmbedder` (lotes em ordem, lista vazia,
contagem e dimensões erradas num único lote, NaN/None nos documentos, erro do Ollama)
não é repetido aqui.
"""

from __future__ import annotations

import dataclasses
import math
import re

import numpy as np
import pytest

from src.chunking import Chunk
from src.retrieval import (
    DEFAULT_TOP_K,
    OLLAMA_EMBED_BATCH_SIZE,
    OLLAMA_QUERY_INSTRUCTION,
    OllamaEmbedder,
    RetrievalError,
    RetrievedChunk,
    VectorIndex,
    build_index,
    retrieve,
)


# ---------------------------------------------------------------- utilitários


def chunk(i: int, text: str | None = None, source: str = "doc.pdf", page: int = 1) -> Chunk:
    return Chunk(
        chunk_id=f"S1-P{page}-C{i}",
        source_name=source,
        page_number=page,
        text=text if text is not None else f"trecho {i}",
    )


class ClienteFalso:
    """Imita `OllamaClient.embed(model, texts) -> list[list[float]]`.

    `gerar(texto) -> list[float]` define o vetor de cada texto. `respostas` permite
    forçar respostas prontas, uma por chamada.
    """

    def __init__(self, gerar=None, respostas=None):
        self.gerar = gerar or (lambda texto: [float(len(texto)), 1.0, 0.5])
        self.respostas = list(respostas) if respostas is not None else None
        self.chamadas: list[dict] = []

    def embed(self, model, texts):
        self.chamadas.append({"model": model, "texts": list(texts)})
        if self.respostas is not None:
            return self.respostas.pop(0)
        return [self.gerar(t) for t in texts]


def vetor_por_indice(texto: str) -> list[float]:
    """'t7' -> [7.0, 1.0]: permite verificar a ordem das linhas na matriz."""
    return [float(texto[1:]), 1.0]


class EmbedderFalso:
    """Embedder com matriz e vetor de consulta fixos; registra as chamadas."""

    def __init__(self, matriz=None, consulta=None, identity: str | None = None):
        if identity is not None:
            self.identity = identity
        self.matriz = matriz
        self.consulta = consulta
        self.docs_chamadas: list[list[str]] = []
        self.query_chamadas: list[str] = []

    def embed_documents(self, texts):
        self.docs_chamadas.append(list(texts))
        return np.asarray(self.matriz, dtype=np.float64)

    def embed_query(self, text):
        self.query_chamadas.append(text)
        return np.asarray(self.consulta, dtype=np.float64)


def indice(linhas, chunks=None) -> VectorIndex:
    linhas = np.asarray(linhas, dtype=np.float64)
    chunks = chunks or [chunk(i) for i in range(len(linhas))]
    return build_index(chunks, EmbedderFalso(matriz=linhas))


def cosseno(a, b) -> float:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


# ---------------------------------------------------------------- constantes e tipos


def test_constantes_do_contrato():
    assert DEFAULT_TOP_K == 4
    assert OLLAMA_EMBED_BATCH_SIZE == 32


def test_retrieved_chunk_e_imutavel():
    item = RetrievedChunk(chunk=chunk(1), score=0.5)
    with pytest.raises(dataclasses.FrozenInstanceError):
        item.score = 1.0  # type: ignore[misc]


# ---------------------------------------------------------------- OllamaEmbedder: lotes


def test_embed_documents_usa_lote_padrao_de_32_na_ordem():
    cliente = ClienteFalso(gerar=vetor_por_indice)
    textos = [f"t{i}" for i in range(70)]
    matriz = OllamaEmbedder(cliente, "m").embed_documents(textos)

    assert [len(c["texts"]) for c in cliente.chamadas] == [32, 32, 6]
    enviados = [t for c in cliente.chamadas for t in c["texts"]]
    assert enviados == textos  # documentos vão puros, sem a instrução da pergunta
    assert matriz.dtype == np.float32
    assert matriz.shape == (70, 2)
    np.testing.assert_array_equal(matriz[:, 0], np.arange(70, dtype=np.float32))


def test_embed_documents_lote_exato_nao_faz_chamada_extra():
    cliente = ClienteFalso(gerar=vetor_por_indice)
    OllamaEmbedder(cliente, "m", batch_size=3).embed_documents([f"t{i}" for i in range(6)])
    assert [len(c["texts"]) for c in cliente.chamadas] == [3, 3]


def test_embed_documents_aceita_tupla():
    cliente = ClienteFalso(gerar=vetor_por_indice)
    matriz = OllamaEmbedder(cliente, "m").embed_documents(("t0", "t1"))
    assert matriz.shape == (2, 2)


@pytest.mark.parametrize("batch_size", [0, -1])
def test_batch_size_menor_que_1_e_recusado(batch_size):
    with pytest.raises(ValueError):
        OllamaEmbedder(ClienteFalso(), "m", batch_size=batch_size)


def test_embed_query_devolve_vetor_float32_1d():
    cliente = ClienteFalso(gerar=lambda t: [1, 2, 3, 4])
    vetor = OllamaEmbedder(cliente, "modelo-emb").embed_query("Qual a taxa?")

    assert cliente.chamadas == [
        {"model": "modelo-emb", "texts": [OLLAMA_QUERY_INSTRUCTION + "Qual a taxa?"]}
    ]
    assert isinstance(vetor, np.ndarray)
    assert vetor.dtype == np.float32
    assert vetor.shape == (4,)
    np.testing.assert_array_equal(vetor, np.array([1, 2, 3, 4], dtype=np.float32))


# ---------------------------------------------------------------- OllamaEmbedder: respostas inválidas


def test_resposta_com_mais_embeddings_que_textos():
    cliente = ClienteFalso(respostas=[[[1.0], [2.0], [3.0]]])
    with pytest.raises(RetrievalError):
        OllamaEmbedder(cliente, "m").embed_documents(["a", "b"])


def test_contagem_errada_em_um_lote_intermediario():
    cliente = ClienteFalso(respostas=[[[1.0, 0.0]], [[1.0, 0.0]]])
    with pytest.raises(RetrievalError):
        OllamaEmbedder(cliente, "m", batch_size=2).embed_documents(["a", "b", "c"])


def test_vetores_de_tamanhos_diferentes_entre_lotes():
    cliente = ClienteFalso(respostas=[[[1.0, 2.0, 3.0]], [[1.0, 2.0]]])
    with pytest.raises(RetrievalError):
        OllamaEmbedder(cliente, "m", batch_size=1).embed_documents(["a", "b"])


@pytest.mark.parametrize(
    "resposta",
    [
        [],  # nenhum embedding
        [[1.0, 2.0], [3.0, 4.0]],  # embeddings demais
        None,  # resposta sem embeddings
        [[0.1, None]],  # valor ausente (o NumPy o converteria em NaN sem reclamar)
        [[0.1, float("nan")]],
        [[0.1, float("inf")]],
        [None],  # vetor ausente
    ],
    ids=["vazia", "demais", "none", "valor_none", "nan", "inf", "vetor_none"],
)
def test_embed_query_com_resposta_invalida_vira_retrieval_error(resposta):
    cliente = ClienteFalso(respostas=[resposta])
    with pytest.raises(RetrievalError):
        OllamaEmbedder(cliente, "m").embed_query("pergunta")


# ---------------------------------------------------------------- build_index


def test_build_index_sem_chunks_da_retrieval_error_sem_chamar_embedder():
    embedder = EmbedderFalso(matriz=np.zeros((0, 0)))
    with pytest.raises(RetrievalError):
        build_index([], embedder)
    assert embedder.docs_chamadas == []


def test_build_index_chama_embed_documents_uma_vez_com_textos_na_ordem():
    chunks = [chunk(1, "alfa"), chunk(2, "beta"), chunk(3, "gama")]
    embedder = EmbedderFalso(matriz=[[1, 0], [0, 1], [1, 1]])
    build_index(chunks, embedder)
    assert embedder.docs_chamadas == [["alfa", "beta", "gama"]]


@pytest.mark.parametrize(
    "matriz",
    [
        np.ones(3),  # 1D
        np.ones((2, 2)),  # linhas a menos
        np.ones((4, 2)),  # linhas a mais
        np.ones((3, 0)),  # d = 0
        np.ones((3, 2, 1)),  # 3D
        np.zeros((0, 0)),
    ],
    ids=["1d", "menos_linhas", "mais_linhas", "d_zero", "3d", "vazia"],
)
def test_build_index_formato_invalido(matriz):
    with pytest.raises(RetrievalError):
        build_index([chunk(1), chunk(2), chunk(3)], EmbedderFalso(matriz=matriz))


def test_build_index_normaliza_linhas_e_mantem_linha_zero():
    idx = indice([[3.0, 4.0], [0.0, 0.0], [0.0, -2.0]])
    assert idx.matrix.dtype == np.float32
    assert idx.matrix.shape == (3, 2)
    assert not np.isnan(idx.matrix).any()
    np.testing.assert_allclose(idx.matrix[0], [0.6, 0.8], rtol=1e-6)
    np.testing.assert_array_equal(idx.matrix[1], [0.0, 0.0])
    np.testing.assert_allclose(idx.matrix[2], [0.0, -1.0], rtol=1e-6)
    normas = np.linalg.norm(idx.matrix, axis=1)
    np.testing.assert_allclose(normas, [1.0, 0.0, 1.0], atol=1e-6)


def test_build_index_preserva_ordem_e_identidade_dos_chunks():
    chunks = [chunk(i, f"texto {i}") for i in range(5)]
    idx = build_index(chunks, EmbedderFalso(matriz=np.eye(5)))
    assert isinstance(idx.chunks, tuple)
    assert len(idx.chunks) == 5
    assert all(a is b for a, b in zip(idx.chunks, chunks))


def test_build_index_aceita_tupla_de_chunks():
    chunks = (chunk(1), chunk(2))
    idx = build_index(chunks, EmbedderFalso(matriz=[[1, 0], [0, 1]]))
    assert idx.chunks == chunks


# ---------------------------------------------------------------- VectorIndex.search


LINHAS = [
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [1.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
    [-1.0, 0.0, 0.0],
    [2.0, 1.0, 1.0],
]


@pytest.mark.parametrize("top_k", [0, -1])
def test_search_top_k_menor_que_1(top_k):
    with pytest.raises(ValueError):
        indice(LINHAS).search(np.array([1.0, 0.0, 0.0]), top_k=top_k)


def test_search_top_k_maior_que_n_devolve_todos():
    idx = indice(LINHAS)
    resultado = idx.search(np.array([1.0, 0.0, 0.0]), top_k=100)
    assert len(resultado) == len(LINHAS)
    assert {id(r.chunk) for r in resultado} == {id(c) for c in idx.chunks}


def test_search_top_k_padrao_e_4():
    resultado = indice(LINHAS).search(np.array([1.0, 0.0, 0.0]))
    assert isinstance(resultado, tuple)
    assert len(resultado) == DEFAULT_TOP_K


@pytest.mark.parametrize("consulta", [[1.0, 0.0], [1.0, 0.0, 0.0, 0.0]], ids=["curta", "longa"])
def test_search_dimensao_errada(consulta):
    with pytest.raises(RetrievalError):
        indice(LINHAS).search(np.array(consulta), top_k=2)


def test_search_consulta_zero_da_score_zero_sem_nan_na_ordem_original():
    idx = indice(LINHAS)
    resultado = idx.search(np.zeros(3), top_k=len(LINHAS))
    assert [r.score for r in resultado] == [0.0] * len(LINHAS)
    assert not any(math.isnan(r.score) for r in resultado)
    assert [r.chunk for r in resultado] == list(idx.chunks)


def test_search_ordena_decrescente_com_scores_de_cosseno():
    consulta = [3.0, 1.0, 0.5]
    idx = indice(LINHAS)
    resultado = idx.search(np.array(consulta), top_k=len(LINHAS))

    scores = [r.score for r in resultado]
    assert scores == sorted(scores, reverse=True)
    esperado = sorted(
        ((cosseno(linha, consulta), i) for i, linha in enumerate(LINHAS)),
        key=lambda par: -par[0],
    )
    assert [r.chunk for r in resultado] == [idx.chunks[i] for _, i in esperado]
    for r, (score, _) in zip(resultado, esperado):
        assert type(r.score) is float
        assert r.score == pytest.approx(score, abs=1e-5)
        assert -1.0 - 1e-6 <= r.score <= 1.0 + 1e-6


def test_search_consulta_nao_normalizada_da_o_mesmo_resultado():
    idx = indice(LINHAS)
    a = idx.search(np.array([3.0, 1.0, 0.5]), top_k=6)
    b = idx.search(np.array([30.0, 10.0, 5.0]), top_k=6)
    assert [r.chunk for r in a] == [r.chunk for r in b]
    assert [r.score for r in a] == pytest.approx([r.score for r in b], abs=1e-6)


def test_search_consulta_float32_ou_float64():
    idx = indice(LINHAS)
    a = idx.search(np.array([1.0, 2.0, 0.0], dtype=np.float32), top_k=3)
    b = idx.search(np.array([1.0, 2.0, 0.0], dtype=np.float64), top_k=3)
    assert [r.chunk for r in a] == [r.chunk for r in b]


def test_search_empate_mantem_ordem_original():
    # Linhas 0, 2 e 4 são idênticas; a 1 é ortogonal; a 3 é oposta.
    linhas = [[1.0, 0.0], [0.0, 1.0], [2.0, 0.0], [-1.0, 0.0], [5.0, 0.0]]
    idx = indice(linhas)
    resultado = idx.search(np.array([1.0, 0.0]), top_k=5)
    assert [r.chunk for r in resultado] == [idx.chunks[i] for i in (0, 2, 4, 1, 3)]
    assert [r.score for r in resultado] == pytest.approx([1.0, 1.0, 1.0, 0.0, -1.0], abs=1e-6)


def test_search_linha_zero_no_indice_tem_score_zero():
    idx = indice([[0.0, 0.0], [1.0, 0.0]])
    resultado = idx.search(np.array([-1.0, 0.0]), top_k=2)
    assert [r.chunk for r in resultado] == [idx.chunks[0], idx.chunks[1]]
    assert [r.score for r in resultado] == pytest.approx([0.0, -1.0], abs=1e-6)
    assert not any(math.isnan(r.score) for r in resultado)


def test_search_devolve_os_mesmos_objetos_do_indice():
    idx = indice(LINHAS)
    for r in idx.search(np.array([0.2, 0.3, 0.9]), top_k=6):
        assert isinstance(r, RetrievedChunk)
        assert any(r.chunk is c for c in idx.chunks)


# ---------------------------------------------------------------- retrieve


@pytest.mark.parametrize("pergunta", ["", "   ", "\n\t "])
def test_retrieve_pergunta_vazia(pergunta):
    embedder = EmbedderFalso(matriz=[[1.0, 0.0]], consulta=[1.0, 0.0])
    idx = build_index([chunk(1)], embedder)
    with pytest.raises(ValueError):
        retrieve(idx, pergunta, embedder)
    assert embedder.query_chamadas == []


def test_retrieve_envia_pergunta_com_strip_e_repassa_top_k():
    embedder = EmbedderFalso(matriz=LINHAS, consulta=[3.0, 1.0, 0.5])
    idx = build_index([chunk(i) for i in range(len(LINHAS))], embedder)

    resultado = retrieve(idx, "  Qual a taxa?\n", embedder, top_k=2)

    assert embedder.query_chamadas == ["Qual a taxa?"]
    assert resultado == idx.search(np.array([3.0, 1.0, 0.5]), top_k=2)
    assert len(resultado) == 2


def test_retrieve_top_k_padrao():
    embedder = EmbedderFalso(matriz=LINHAS, consulta=[1.0, 0.0, 0.0])
    idx = build_index([chunk(i) for i in range(len(LINHAS))], embedder)
    assert len(retrieve(idx, "pergunta", embedder)) == DEFAULT_TOP_K


def test_retrieve_top_k_invalido():
    embedder = EmbedderFalso(matriz=LINHAS, consulta=[1.0, 0.0, 0.0])
    idx = build_index([chunk(i) for i in range(len(LINHAS))], embedder)
    with pytest.raises(ValueError):
        retrieve(idx, "pergunta", embedder, top_k=0)


def test_build_index_guarda_a_identity_do_embedder():
    embedder = EmbedderFalso(matriz=[[1.0, 0.0]], identity="falso:a")
    assert build_index([chunk(1)], embedder).embedder_id == "falso:a"
    assert build_index([chunk(1)], EmbedderFalso(matriz=[[1.0, 0.0]])).embedder_id is None


@pytest.mark.parametrize(
    "id_indice, id_busca",
    [("falso:a", "falso:b"), ("falso:a", None), (None, "falso:b")],
    ids=["outro_modelo", "busca_sem_identity", "indice_sem_identity"],
)
def test_retrieve_recusa_embedder_com_outra_identity(id_indice, id_busca):
    # Mesma dimensão: sem a checagem, a busca "funcionaria" e traria trechos aleatórios.
    idx = build_index([chunk(1)], EmbedderFalso(matriz=[[1.0, 0.0]], identity=id_indice))
    outro = EmbedderFalso(consulta=[1.0, 0.0], identity=id_busca)
    with pytest.raises(RetrievalError) as info:
        retrieve(idx, "pergunta", outro)
    assert "Processar documentos" in str(info.value)
    assert outro.query_chamadas == []  # recusa antes de gastar uma chamada ao modelo


def test_retrieve_aceita_embedder_com_a_mesma_identity():
    idx = build_index([chunk(1)], EmbedderFalso(matriz=[[1.0, 0.0]], identity="falso:a"))
    outro = EmbedderFalso(consulta=[1.0, 0.0], identity="falso:a")
    assert len(retrieve(idx, "pergunta", outro)) == 1


# ---------------------------------------------------------------- ponta a ponta com saco de palavras

VOCABULARIO = (
    "salão festas churrasqueira piscina quadra taxa reserva valor pessoas limpeza "
    "condominial assembleia elevadores manutenção silêncio obras"
).split()


def saco_de_palavras(texto: str) -> list[float]:
    palavras = re.findall(r"\w+", texto.lower())
    return [float(palavras.count(termo)) for termo in VOCABULARIO]


class EmbedderSacoDePalavras:
    def embed_documents(self, texts):
        return np.array([saco_de_palavras(t) for t in texts], dtype=np.float32)

    def embed_query(self, text):
        return np.array(saco_de_palavras(text), dtype=np.float32)


CHUNKS_AMOSTRA = (
    Chunk(
        "S1-P3-C1",
        "regulamento_condominio.pdf",
        3,
        "Salão de festas: reserva com 15 dias de antecedência, taxa de R$ 150,00, "
        "capacidade de 60 pessoas, uso até 1h.",
    ),
    Chunk(
        "S1-P3-C2",
        "regulamento_condominio.pdf",
        3,
        "Churrasqueira: reserva com 7 dias de antecedência, taxa de R$ 80,00, "
        "capacidade de 20 pessoas, uso até 22h. Taxa de limpeza R$ 90,00.",
    ),
    Chunk(
        "S1-P2-C1",
        "regulamento_condominio.pdf",
        2,
        "Silêncio das 22h às 7h. Obras com ruído de segunda a sexta, das 8h às 17h.",
    ),
    Chunk(
        "S2-P1-C1",
        "ata_assembleia_2026.pdf",
        1,
        "A assembleia aprovou a taxa condominial de R$ 680,00 a partir de maio de 2026.",
    ),
    Chunk(
        "S3-P1-C1",
        "aviso_com_pagina_em_branco.pdf",
        1,
        "Manutenção dos elevadores do Bloco B em 20/10/2026, das 9h às 15h.",
    ),
)


@pytest.mark.parametrize(
    "pergunta, chunk_id",
    [
        ("Qual o valor da taxa de reserva da churrasqueira?", "S1-P3-C2"),
        ("Quanto custa a reserva do salão de festas?", "S1-P3-C1"),
        ("Quando é a manutenção dos elevadores?", "S3-P1-C1"),
        ("Qual o horário de silêncio e de obras?", "S1-P2-C1"),
    ],
)
def test_ponta_a_ponta_traz_o_trecho_certo_em_primeiro(pergunta, chunk_id):
    embedder = EmbedderSacoDePalavras()
    idx = build_index(CHUNKS_AMOSTRA, embedder)
    resultado = retrieve(idx, pergunta, embedder)

    assert resultado[0].chunk.chunk_id == chunk_id
    assert resultado[0].score > resultado[1].score
    assert all(any(r.chunk is c for c in CHUNKS_AMOSTRA) for r in resultado)


def test_ponta_a_ponta_churrasqueira_vence_o_salao_distrator():
    embedder = EmbedderSacoDePalavras()
    idx = build_index(CHUNKS_AMOSTRA, embedder)
    resultado = retrieve(idx, "Qual o valor da taxa de reserva da churrasqueira?", embedder)
    primeiro = resultado[0].chunk
    assert (primeiro.source_name, primeiro.page_number) == ("regulamento_condominio.pdf", 3)
    assert "R$ 80,00" in primeiro.text
    ids = [r.chunk.chunk_id for r in resultado]
    assert ids.index("S1-P3-C2") < ids.index("S1-P3-C1")


def test_ponta_a_ponta_pelo_ollama_embedder_com_cliente_falso():
    cliente = ClienteFalso(gerar=saco_de_palavras)
    embedder = OllamaEmbedder(cliente, "qwen3-embedding:0.6b", batch_size=2)
    idx = build_index(CHUNKS_AMOSTRA, embedder)
    resultado = retrieve(idx, "  Qual o valor da taxa de reserva da churrasqueira?  ", embedder)

    assert resultado[0].chunk is CHUNKS_AMOSTRA[1]
    assert idx.embedder_id == "ollama:qwen3-embedding:0.6b"
    assert [len(c["texts"]) for c in cliente.chamadas] == [2, 2, 1, 1]
    assert {c["model"] for c in cliente.chamadas} == {"qwen3-embedding:0.6b"}
    assert cliente.chamadas[-1]["texts"] == [
        OLLAMA_QUERY_INSTRUCTION + "Qual o valor da taxa de reserva da churrasqueira?"
    ]


# ---------------------------------------------------------------- lacunas apontadas na revisão (mutação)


def test_score_nunca_passa_de_1_mesmo_com_arredondamento_float32():
    # Em float32, o produto de um vetor normalizado por ele mesmo pode dar 1.0000002.
    rng = np.random.default_rng(7)
    matriz = rng.normal(size=(200, 3072)).astype(np.float32)
    indice = build_index([chunk(i) for i in range(200)], EmbedderFalso(matriz))
    for i in range(0, 200, 10):
        resultado = indice.search(matriz[i], top_k=1)
        assert resultado[0].score <= 1.0


def test_desempate_estavel_com_muitas_linhas_iguais():
    # O quicksort do NumPy só é estável por acaso com menos de 16 elementos.
    matriz = np.ones((60, 4), dtype=np.float32)
    trechos = [chunk(i) for i in range(60)]
    indice = build_index(trechos, EmbedderFalso(matriz))
    resultado = indice.search(np.ones(4, dtype=np.float32), top_k=60)
    assert [r.chunk for r in resultado] == trechos


@pytest.mark.parametrize("valor", [np.nan, np.inf])
def test_embeddings_nao_finitos_sao_recusados_no_indice(valor):
    matriz = np.ones((2, 3), dtype=np.float32)
    matriz[1, 0] = valor
    with pytest.raises(RetrievalError):
        build_index([chunk(0), chunk(1)], EmbedderFalso(matriz))


def test_consulta_nao_finita_e_recusada():
    indice = build_index([chunk(0)], EmbedderFalso(np.ones((1, 3), dtype=np.float32)))
    with pytest.raises(RetrievalError):
        indice.search(np.array([1.0, np.nan, 0.0], dtype=np.float32))


def test_matriz_do_indice_e_somente_leitura():
    indice = build_index([chunk(0)], EmbedderFalso(np.ones((1, 3), dtype=np.float32)))
    with pytest.raises(ValueError):
        indice.matrix[0, 0] = 5.0


def test_normalizacao_nao_estoura_com_valores_grandes():
    matriz = np.full((1, 4), 1e30, dtype=np.float32)
    indice = build_index([chunk(0)], EmbedderFalso(matriz))
    assert np.linalg.norm(indice.matrix[0]) == pytest.approx(1.0, abs=1e-5)


def test_consulta_em_formato_2d_e_recusada():
    indice = build_index([chunk(0)], EmbedderFalso(np.ones((1, 3), dtype=np.float32)))
    with pytest.raises(RetrievalError):
        indice.search(np.ones((1, 3), dtype=np.float32))
