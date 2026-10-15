"""Testes de caixa-preta do `src/chunking.py`, escritos somente a partir de
`docs/contratos/chunking.md` e do gabarito `docs/amostras/FATOS.md`.

As amostras reais são carregadas com `src.loader.load_pdf`; os casos sintéticos montam
`PageText` à mão. Os testes de propriedade usam `random` com semente fixa, então são
determinísticos.
"""

from __future__ import annotations

import dataclasses
import random
import re
import string
import unicodedata
from pathlib import Path

import pytest

from src.chunking import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_OVERLAP,
    Chunk,
    chunk_pages,
    normalize_text,
    split_spans,
)
from src.loader import PageText, load_pdf

AMOSTRAS = Path(__file__).resolve().parent.parent / "docs" / "amostras"

REGULAMENTO = "regulamento_condominio.pdf"
ATA = "ata_assembleia_2026.pdf"
AVISO = "aviso_com_pagina_em_branco.pdf"

ID_RE = re.compile(r"^S(\d+)-P(\d+)-C(\d+)$")


# ---------------------------------------------------------------- utilitários


def paginas_amostra(nome: str) -> tuple[PageText, ...]:
    return load_pdf((AMOSTRAS / nome).read_bytes(), nome).pages


def checar_invariantes(text: str, spans, chunk_size: int, overlap: int) -> None:
    """Confere os invariantes 1–5 de `split_spans` e os casos triviais do contrato."""
    ctx = f"text={text!r:.120} chunk_size={chunk_size} overlap={overlap} spans={spans!r:.300}"
    assert isinstance(spans, list), ctx
    if text == "":
        assert spans == [], ctx
        return
    assert spans, ctx
    for span in spans:
        assert isinstance(span, tuple) and len(span) == 2, ctx
        assert all(isinstance(x, int) for x in span), ctx
    if len(text) <= chunk_size:
        assert spans == [(0, len(text))], ctx

    inicios = [s for s, _ in spans]
    fins = [f for _, f in spans]

    # 1. primeiro início 0, último fim len(text)
    assert inicios[0] == 0, ctx
    assert fins[-1] == len(text), ctx
    # 2. 0 < fim - inicio <= chunk_size
    for s, f in spans:
        assert 0 < f - s <= chunk_size, ctx
    for i in range(len(spans) - 1):
        # 3. inícios e fins estritamente crescentes
        assert inicios[i + 1] > inicios[i], ctx
        assert fins[i + 1] > fins[i], ctx
        # 4. cobertura sem buracos
        assert inicios[i + 1] <= fins[i], ctx
        # 5. sobreposição nunca passa de `overlap`...
        assert fins[i] - inicios[i + 1] <= overlap, ctx
        # ...e existe sempre que for possível sem violar 2–3. Com fim - inicio >= 2 há
        # um início estritamente entre os dois, e o próximo fim pode passar de fins[i]
        # sem exceder chunk_size; com 1 caractere não há como sobrepor.
        if overlap > 0 and fins[i] - inicios[i] >= 2:
            assert inicios[i + 1] < fins[i], ctx


def texto_palavras(rng: random.Random, n_palavras: int, max_len: int) -> str:
    """Texto já normalizado: palavras separadas por um único espaço, com pontuação."""
    letras = string.ascii_letters + "áéíóúãõçÁÉ0123456789"
    palavras = []
    for _ in range(n_palavras):
        palavra = "".join(rng.choice(letras) for _ in range(rng.randint(1, max_len)))
        if rng.random() < 0.25 and len(palavra) < max_len:
            palavra += rng.choice(".!?;,:")
        palavras.append(palavra)
    return " ".join(palavras)


def texto_sem_espacos(rng: random.Random, n: int) -> str:
    return "".join(rng.choice(string.ascii_lowercase + ".!?;") for _ in range(n))


def texto_bruto(rng: random.Random, n: int) -> str:
    """Qualquer texto: espaços repetidos, quebras de linha, pontas com espaço."""
    return "".join(rng.choice("abcde .!?;\n\t  ") for _ in range(n))


# ---------------------------------------------------------------- constantes e Chunk


def test_constantes_padrao():
    assert DEFAULT_CHUNK_SIZE == 1000
    assert DEFAULT_OVERLAP == 150


def test_chunk_e_imutavel():
    chunk = Chunk(chunk_id="S1-P1-C1", source_name="a.pdf", page_number=1, text="x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        chunk.text = "y"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        chunk.chunk_id = "S9-P9-C9"  # type: ignore[misc]


def test_chunk_devolvido_por_chunk_pages_e_imutavel():
    (chunk,) = chunk_pages([PageText("a.pdf", 1, "texto curto")])
    assert isinstance(chunk, Chunk)
    with pytest.raises(dataclasses.FrozenInstanceError):
        chunk.page_number = 2  # type: ignore[misc]


# ---------------------------------------------------------------- normalize_text


def test_normalize_nfc_compoe_acento_decomposto():
    assert normalize_text("á") == "á"
    assert normalize_text("Café com ça") == "Café com ça"
    assert normalize_text("á") == unicodedata.normalize("NFC", "á")


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("a\x00b", "a b"),
        ("a\x00\x00b", "a b"),
        ("a\x07b\x1bc\x7fd", "a b c d"),
        ("\x00abc\x00", "abc"),
        ("a \x00 b", "a b"),
    ],
)
def test_normalize_controles_viram_espaco(entrada, esperado):
    assert normalize_text(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("a\nb", "a b"),
        ("a\n\n\nb", "a b"),
        ("a\tb", "a b"),
        ("a\xa0b", "a b"),
        ("a \n\t\xa0 \r\n b", "a b"),
        ("um  dois   tres", "um dois tres"),
    ],
)
def test_normalize_colapsa_espacos(entrada, esperado):
    assert normalize_text(entrada) == esperado


def test_normalize_strip_nas_pontas():
    assert normalize_text("  \n\t olá mundo \xa0\n ") == "olá mundo"


@pytest.mark.parametrize("entrada", ["", " ", "\n\t\xa0", "\x00\x00", " \x00 \n "])
def test_normalize_so_brancos_vira_vazio(entrada):
    assert normalize_text(entrada) == ""


def test_normalize_preserva_hifen():
    assert normalize_text("segunda-\nfeira") == "segunda- feira"
    assert normalize_text("quinta-feira") == "quinta-feira"


def test_normalize_nao_muda_caixa_pontuacao_nem_acentos():
    texto = "Art. 7º A Piscina funciona de TERÇA a domingo; taxa: R$ 80,00! (sim?)"
    assert normalize_text(texto) == texto


def test_normalize_propriedade_contra_referencia():
    """Compara com uma implementação literal dos 4 passos, em textos aleatórios."""

    def referencia(t: str) -> str:
        t = unicodedata.normalize("NFC", t)
        t = "".join(" " if unicodedata.category(c) == "Cc" else c for c in t)
        t = re.sub(r"\s+", " ", t)
        return t.strip()

    alfabeto = "aeiouAÉḉ̧ \n\t\r\xa0\x00\x01\x1f\x7f-.,;R$0123"
    rng = random.Random(20260927)
    for _ in range(500):
        texto = "".join(rng.choice(alfabeto) for _ in range(rng.randint(0, 60)))
        saida = normalize_text(texto)
        assert saida == referencia(texto), repr(texto)
        assert normalize_text(saida) == saida, repr(texto)  # idempotente
        assert "  " not in saida and saida == saida.strip(), repr(texto)


# ---------------------------------------------------------------- split_spans: básicos


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (-1, 0), (10, -1), (10, 10), (10, 11), (1, 1)],
)
@pytest.mark.parametrize("texto", ["", "abc", "um texto qualquer " * 20])
def test_split_spans_parametros_invalidos(texto, chunk_size, overlap):
    with pytest.raises(ValueError):
        split_spans(texto, chunk_size, overlap)


def test_split_spans_texto_vazio():
    assert split_spans("") == []
    assert split_spans("", 5, 2) == []


@pytest.mark.parametrize(
    ("texto", "chunk_size", "overlap"),
    [("a", 1, 0), ("abc", 3, 2), ("abc", 10, 0), ("dois termos", 11, 5), ("x" * 1000, 1000, 150)],
)
def test_split_spans_texto_curto(texto, chunk_size, overlap):
    assert split_spans(texto, chunk_size, overlap) == [(0, len(texto))]


def test_split_spans_usa_padroes():
    assert split_spans("x" * 1000) == [(0, 1000)]
    # 1001 caracteres sem espaço: corte seco em 1000, próximo início em 1000 - 150.
    assert split_spans("x" * 1001) == [(0, 1000), (850, 1001)]


# ---------------------------------------------------------------- split_spans: invariantes


def test_invariantes_texto_sem_espacos_corte_seco():
    texto = "x" * 25
    spans = split_spans(texto, 10, 3)
    checar_invariantes(texto, spans, 10, 3)
    assert spans == [(0, 10), (7, 17), (14, 24), (21, 25)]


def test_invariantes_overlap_igual_chunk_size_menos_1():
    texto = "abcdefghij" * 5
    spans = split_spans(texto, 5, 4)
    checar_invariantes(texto, spans, 5, 4)
    assert spans == [(i, i + 5) for i in range(46)]


@pytest.mark.parametrize("chunk_size", [2, 3, 7, 20])
def test_invariantes_overlap_maximo_com_espacos(chunk_size):
    rng = random.Random(chunk_size)
    texto = texto_palavras(rng, 60, 12)
    overlap = chunk_size - 1
    checar_invariantes(texto, split_spans(texto, chunk_size, overlap), chunk_size, overlap)


def test_invariantes_palavras_maiores_que_chunk_size():
    texto = "curta " + "a" * 37 + " meio " + "b" * 50 + " fim"
    for chunk_size, overlap in [(10, 0), (10, 3), (10, 9), (15, 5), (36, 20)]:
        checar_invariantes(texto, split_spans(texto, chunk_size, overlap), chunk_size, overlap)


def test_invariantes_chunk_size_1():
    texto = "a b.c d"
    spans = split_spans(texto, 1, 0)
    checar_invariantes(texto, spans, 1, 0)
    assert spans == [(i, i + 1) for i in range(len(texto))]


def test_overlap_zero_nao_sobrepoe():
    rng = random.Random(7)
    texto = texto_palavras(rng, 200, 9)
    spans = split_spans(texto, 50, 0)
    checar_invariantes(texto, spans, 50, 0)
    for (_, fim), (inicio, _) in zip(spans, spans[1:]):
        assert inicio == fim


def test_sobreposicao_no_maximo_overlap():
    rng = random.Random(11)
    texto = texto_palavras(rng, 400, 10)
    for chunk_size, overlap in [(100, 30), (200, 150), (60, 1), (1000, 150)]:
        spans = split_spans(texto, chunk_size, overlap)
        checar_invariantes(texto, spans, chunk_size, overlap)
        assert len(spans) > 1
        for (_, fim), (inicio, _) in zip(spans, spans[1:]):
            assert 0 < fim - inicio <= overlap


def test_propriedade_invariantes_textos_aleatorios():
    """Centenas de textos sintéticos e combinações de chunk_size/overlap."""
    rng = random.Random(1234567)
    casos = 0
    for _ in range(900):
        chunk_size = rng.choice([1, 2, 3, 5, 8, 13, 20, 40, 64, 100, rng.randint(1, 150)])
        overlap = rng.choice([0, chunk_size - 1, chunk_size // 2, rng.randint(0, chunk_size - 1)])
        tipo = rng.randrange(4)
        if tipo == 0:
            texto = texto_palavras(rng, rng.randint(1, 80), rng.randint(1, 15))
        elif tipo == 1:
            texto = texto_sem_espacos(rng, rng.randint(1, 300))
        elif tipo == 2:  # palavras maiores que chunk_size
            texto = texto_palavras(rng, rng.randint(1, 10), 3 * chunk_size + 2)
        else:  # "qualquer texto não vazio", mesmo sem normalizar
            texto = texto_bruto(rng, rng.randint(1, 200))
        spans = split_spans(texto, chunk_size, overlap)
        checar_invariantes(texto, spans, chunk_size, overlap)
        casos += 1
    assert casos == 900


def test_propriedade_invariantes_padroes_textos_longos():
    rng = random.Random(42)
    for _ in range(40):
        texto = texto_palavras(rng, rng.randint(50, 1200), rng.randint(3, 14))
        checar_invariantes(texto, split_spans(texto), DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP)


def test_propriedade_trechos_sem_espaco_nas_pontas():
    """Palavras curtas e overlap folgado: nunca há corte seco, então nenhum trecho começa
    ou termina com espaço, começa no início de uma palavra e termina antes de um espaço."""
    rng = random.Random(99)
    for _ in range(300):
        chunk_size = rng.randint(40, 120)
        overlap = rng.randint(12, chunk_size // 2 - 2)
        texto = texto_palavras(rng, rng.randint(5, 120), 10)
        spans = split_spans(texto, chunk_size, overlap)
        checar_invariantes(texto, spans, chunk_size, overlap)
        for s, f in spans:
            ctx = f"{texto!r} cs={chunk_size} ov={overlap} span={(s, f)}"
            assert texto[s] != " " and texto[f - 1] != " ", ctx
            assert s == 0 or texto[s - 1] == " ", ctx
            assert f == len(texto) or texto[f] == " ", ctx


# ---------------------------------------------------------------- split_spans: corte preferencial


@pytest.mark.parametrize("pontuacao", [".", "!", "?", ";"])
def test_corte_preferencial_em_fim_de_frase(pontuacao):
    texto = "Palavras iniciais aqui. Mais texto vem depois sem ponto algum aqui no final"
    texto = texto.replace(".", pontuacao)
    assert texto[22] == pontuacao and texto[40] != " "
    spans = split_spans(texto, 40, 0)
    checar_invariantes(texto, spans, 40, 0)
    # O último espaço da janela está em 38, mas o fim de frase (segunda metade) vence.
    assert spans[0] == (0, 23)


def test_corte_no_ultimo_fim_de_frase_da_janela():
    texto = "Aaaa bbbb cccc. Dddd eee. Ffff gggg hhhh iiii jjjj"
    spans = split_spans(texto, 30, 0)
    checar_invariantes(texto, spans, 30, 0)
    assert spans[0] == (0, 25)


def test_fim_de_frase_na_primeira_metade_e_ignorado():
    texto = "Oi. Depois vem um texto longo sem nenhum ponto final ate acabar"
    assert texto[39] != " " and texto.rfind(" ", 0, 40) == 33
    spans = split_spans(texto, 39, 0)
    checar_invariantes(texto, spans, 39, 0)
    assert spans[0] == (0, 33)


def test_ponto_sem_espaco_nao_e_fim_de_frase():
    texto = "O valor total ficou em R$ 1.500 mais taxas e outros custos"
    assert texto[27] == "." and texto[40] != " " and texto.rfind(" ", 0, 41) == 36
    spans = split_spans(texto, 40, 0)
    checar_invariantes(texto, spans, 40, 0)
    assert spans[0] == (0, 36)


def test_corte_em_espaco_e_inicio_no_comeco_da_palavra():
    texto = "aaaa bbbb cccc dddd eeee ffff"
    esperado = [(0, 9), (5, 14), (10, 19), (15, 24), (20, 29)]
    # fim - overlap cai exatamente no começo de uma palavra (overlap 4)...
    assert split_spans(texto, 12, 4) == esperado
    # ...ou no meio de uma e é avançado até a próxima palavra (overlap 6).
    assert split_spans(texto, 12, 6) == esperado


def test_ajuste_sem_sobreposicao_mantem_fim_menos_overlap():
    texto = "abcdefghij klmnopqrst"
    # Corte no espaço (10); 10 - 3 = 7 cai no meio da palavra e a próxima palavra começa
    # em 11, sem sobreposição: o início fica em 7.
    assert split_spans(texto, 15, 3) == [(0, 10), (7, 21)]


def test_corte_seco_sem_espaco_na_janela():
    texto = "abcdefghijklmnopqrstuvwxyz fim"
    spans = split_spans(texto, 10, 0)
    checar_invariantes(texto, spans, 10, 0)
    assert spans[0] == (0, 10)
    assert spans[1] == (10, 20)


# ---------------------------------------------------------------- chunk_pages


def test_chunk_pages_vazio():
    assert chunk_pages([]) == ()
    assert chunk_pages(()) == ()


@pytest.mark.parametrize(("chunk_size", "overlap"), [(0, 0), (-5, 0), (10, -1), (10, 10), (5, 9)])
def test_chunk_pages_valida_parametros_mesmo_sem_paginas(chunk_size, overlap):
    with pytest.raises(ValueError):
        chunk_pages([], chunk_size, overlap)
    with pytest.raises(ValueError):
        chunk_pages([PageText("a.pdf", 1, "texto")], chunk_size, overlap)


def test_chunk_pages_devolve_tupla_de_chunks():
    resultado = chunk_pages([PageText("a.pdf", 1, "um"), PageText("a.pdf", 2, "dois")])
    assert isinstance(resultado, tuple)
    assert all(isinstance(c, Chunk) for c in resultado)


def test_chunk_pages_formato_e_unicidade_dos_ids():
    rng = random.Random(5)
    pages = [
        PageText(nome, n, texto_palavras(rng, rng.randint(1, 60), 9))
        for nome in ("a.pdf", "b.pdf", "c.pdf")
        for n in (1, 2, 3)
    ]
    chunks = chunk_pages(pages, 50, 10)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    for chunk in chunks:
        m = ID_RE.match(chunk.chunk_id)
        assert m, chunk.chunk_id
        assert int(m.group(2)) == chunk.page_number


def test_chunk_pages_numeracao_s_pela_primeira_aparicao_intercalada():
    pages = [
        PageText("zeta.pdf", 1, "primeira pagina de zeta"),
        PageText("alfa.pdf", 1, "primeira pagina de alfa"),
        PageText("zeta.pdf", 2, "segunda pagina de zeta"),
        PageText("meio.pdf", 1, "unica pagina de meio"),
        PageText("alfa.pdf", 2, "segunda pagina de alfa"),
    ]
    ids = [c.chunk_id for c in chunk_pages(pages)]
    assert ids == ["S1-P1-C1", "S2-P1-C1", "S1-P2-C1", "S3-P1-C1", "S2-P2-C1"]


def test_chunk_pages_respeita_ordem_recebida():
    pages = [PageText("a.pdf", 3, "tres"), PageText("a.pdf", 1, "um")]
    chunks = chunk_pages(pages)
    assert [c.chunk_id for c in chunks] == ["S1-P3-C1", "S1-P1-C1"]
    assert [c.text for c in chunks] == ["tres", "um"]


def test_chunk_pages_c_por_pagina_e_texto_igual_a_fatia():
    rng = random.Random(8)
    pages = [
        PageText("a.pdf", 1, "  " + texto_palavras(rng, 80, 9).replace(" ", " \n", 7)),
        PageText("a.pdf", 2, texto_palavras(rng, 5, 6)),
        PageText("b.pdf", 7, texto_palavras(rng, 150, 11) + "\x00\t"),
    ]
    chunk_size, overlap = 60, 15
    chunks = chunk_pages(pages, chunk_size, overlap)

    esperado = []
    for page in pages:
        norm = normalize_text(page.text)
        n = 1 if page.source_name == "a.pdf" else 2
        for k, (s, f) in enumerate(split_spans(norm, chunk_size, overlap), start=1):
            esperado.append((f"S{n}-P{page.page_number}-C{k}", page.source_name,
                             page.page_number, norm[s:f]))
    assert [(c.chunk_id, c.source_name, c.page_number, c.text) for c in chunks] == esperado
    assert sum(1 for c in chunks if c.page_number == 1) > 1  # página 1 tem vários trechos


def test_chunk_pages_pula_paginas_vazias_depois_da_normalizacao():
    pages = [
        PageText("a.pdf", 1, "texto da pagina um"),
        PageText("a.pdf", 2, " \n\x00\t\xa0 "),
        PageText("a.pdf", 3, "texto da pagina tres"),
    ]
    chunks = chunk_pages(pages)
    assert [c.chunk_id for c in chunks] == ["S1-P1-C1", "S1-P3-C1"]
    assert all(c.page_number != 2 for c in chunks)


def test_chunk_pages_so_paginas_vazias_devolve_tupla_vazia():
    assert chunk_pages([PageText("a.pdf", 1, "\x00"), PageText("b.pdf", 1, "\n ")]) == ()


def test_chunk_pages_s_conta_aparicao_de_pagina_vazia():
    """Leitura literal: `n` é a primeira aparição do `source_name` em `pages`, mesmo que
    as páginas desse arquivo sejam todas puladas por ficarem vazias."""
    pages = [PageText("vazio.pdf", 1, "\x00 \n"), PageText("cheio.pdf", 1, "conteudo")]
    assert [c.chunk_id for c in chunk_pages(pages)] == ["S2-P1-C1"]


def test_chunk_pages_copia_source_name_e_page_number():
    pages = [PageText("Relatório Final.pdf", 42, "conteúdo da página quarenta e dois")]
    (chunk,) = chunk_pages(pages)
    assert chunk.source_name == "Relatório Final.pdf"
    assert chunk.page_number == 42
    assert chunk.chunk_id == "S1-P42-C1"
    assert chunk.text == "conteúdo da página quarenta e dois"


def test_chunk_pages_normaliza_texto():
    (chunk,) = chunk_pages([PageText("a.pdf", 1, "  segunda-\nfeira\x00á \t ")])
    assert chunk.text == "segunda- feira á"


def test_chunk_pages_deterministico():
    rng = random.Random(3)
    pages = [PageText(f"doc{i % 2}.pdf", i, texto_palavras(rng, 120, 10)) for i in range(1, 6)]
    assert chunk_pages(pages, 80, 20) == chunk_pages(list(pages), 80, 20)
    assert chunk_pages(pages) == chunk_pages(tuple(pages))


def test_nenhum_trecho_atravessa_paginas():
    rng = random.Random(21)
    corpo1 = texto_palavras(rng, 40, 8)
    corpo2 = texto_palavras(rng, 40, 8)
    pages = [
        PageText("a.pdf", 1, corpo1 + " FIMDAUM"),
        PageText("a.pdf", 2, "INICIODOIS " + corpo2),
    ]
    for chunk_size, overlap in [(30, 10), (100, 50), (10_000, 150)]:
        chunks = chunk_pages(pages, chunk_size, overlap)
        for chunk in chunks:
            proprio = normalize_text(pages[chunk.page_number - 1].text)
            assert chunk.text in proprio
            assert not ("FIMDAUM" in chunk.text and "INICIODOIS" in chunk.text)
        if chunk_size == 10_000:
            # Mesmo cabendo tudo num trecho, cada página gera o seu.
            assert [c.chunk_id for c in chunks] == ["S1-P1-C1", "S1-P2-C1"]
            assert chunks[0].text.endswith("FIMDAUM")
            assert chunks[1].text.startswith("INICIODOIS")


# ---------------------------------------------------------------- amostras reais


def test_amostra_regulamento_7_trechos():
    pages = paginas_amostra(REGULAMENTO)
    chunks = chunk_pages(pages)
    assert [c.chunk_id for c in chunks] == [
        "S1-P1-C1",
        "S1-P2-C1",
        "S1-P3-C1",
        "S1-P3-C2",
        "S1-P4-C1",
        "S1-P5-C1",
        "S1-P6-C1",
    ]
    assert all(c.source_name == REGULAMENTO for c in chunks)
    for chunk in chunks:
        assert len(chunk.text) <= DEFAULT_CHUNK_SIZE
        pagina = next(p for p in pages if p.page_number == chunk.page_number)
        assert chunk.text in normalize_text(pagina.text)

    # Os dois trechos da página 3 se sobrepõem em no máximo 150 caracteres.
    p3 = normalize_text(next(p for p in pages if p.page_number == 3).text)
    (s1, f1), (s2, f2) = split_spans(p3)
    assert 0 < f1 - s2 <= DEFAULT_OVERLAP
    c1, c2 = (c for c in chunks if c.page_number == 3)
    assert (c1.text, c2.text) == (p3[s1:f1], p3[s2:f2])


def test_amostra_ata_2_trechos():
    chunks = chunk_pages(paginas_amostra(ATA))
    assert [c.chunk_id for c in chunks] == ["S1-P1-C1", "S1-P2-C1"]


def test_amostra_aviso_2_trechos_sem_pagina_2():
    chunks = chunk_pages(paginas_amostra(AVISO))
    assert [c.chunk_id for c in chunks] == ["S1-P1-C1", "S1-P3-C1"]
    assert [c.page_number for c in chunks] == [1, 3]


def test_amostras_juntas_numeradas_s1_s2_s3():
    pages = paginas_amostra(REGULAMENTO) + paginas_amostra(ATA) + paginas_amostra(AVISO)
    chunks = chunk_pages(pages)
    assert len(chunks) == 11
    prefixos = {"S1": REGULAMENTO, "S2": ATA, "S3": AVISO}
    for chunk in chunks:
        assert prefixos[chunk.chunk_id.split("-")[0]] == chunk.source_name
    assert [c.chunk_id.split("-")[0] for c in chunks] == ["S1"] * 7 + ["S2"] * 2 + ["S3"] * 2
    assert len({c.chunk_id for c in chunks}) == 11


@pytest.mark.parametrize(
    ("fato", "onde"),
    [
        ("48 unidades", {(REGULAMENTO, 1), (ATA, 1)}),
        ("16 apartamentos", {(REGULAMENTO, 1)}),
        ("Marta Figueiredo", {(REGULAMENTO, 1), (ATA, 2)}),
        ("das 9h às 13h", {(REGULAMENTO, 2)}),
        ("R$ 80,00", {(REGULAMENTO, 3)}),
        ("R$ 150,00", {(REGULAMENTO, 3)}),
        ("R$ 90,00", {(REGULAMENTO, 3)}),
        ("1 vaga de garagem", {(REGULAMENTO, 4)}),
        ("48 horas", {(REGULAMENTO, 5)}),
        ("prazo de 15 dias", {(REGULAMENTO, 6)}),
        ("R$ 680,00", {(ATA, 1)}),
        ("R$ 42.000,00", {(ATA, 2)}),
        ("20 de outubro de 2026", {(AVISO, 1)}),
        ("escadas", {(AVISO, 3)}),
    ],
)
def test_fatos_no_trecho_da_pagina_certa(fato, onde):
    pages = paginas_amostra(REGULAMENTO) + paginas_amostra(ATA) + paginas_amostra(AVISO)
    chunks = chunk_pages(pages)
    com_fato = {(c.source_name, c.page_number) for c in chunks if fato in c.text}
    assert com_fato == onde


# ---------------------------------------------------------------- lacunas apontadas na revisão (mutação)


def test_espaco_exatamente_no_fim_da_janela_vale_como_corte():
    assert split_spans("aaaa bbbb cccc", 9, 0)[0] == (0, 9)


def test_fim_de_frase_exatamente_na_metade_da_janela_vale():
    assert split_spans("abcd. fg hijkl", 10, 0)[0] == (0, 5)


def test_fim_de_frase_antes_da_metade_e_ignorado_mesmo_perto_dela():
    assert split_spans("aaaa. bbbb cc ddd", 12, 0)[0] == (0, 10)


def test_texto_do_trecho_e_a_fatia_exata_sem_strip():
    pagina = PageText("a.pdf", 1, "aaaa bbbb cccc dddd")
    assert [c.text for c in chunk_pages([pagina], 9, 0)] == ["aaaa bbbb", " cccc", " dddd"]


def test_pagina_repetida_na_entrada_e_recusada():
    paginas = [PageText("a.pdf", 1, "texto um"), PageText("a.pdf", 1, "texto dois")]
    with pytest.raises(ValueError):
        chunk_pages(paginas)
