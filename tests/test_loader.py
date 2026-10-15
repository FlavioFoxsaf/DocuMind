"""Testes de caixa-preta do `src/loader.py`, escritos somente a partir de
`docs/contratos/loader.md` e do gabarito `docs/amostras/FATOS.md`.

Nada é gravado em disco: os PDFs extras são gerados em memória com `pypdf` ou `fpdf2`.
"""

from __future__ import annotations

import dataclasses
import io
import re
from pathlib import Path

import pypdf
import pytest
from fpdf import FPDF
from pypdf import PdfReader, PdfWriter

from src.loader import (
    MAX_FILE_BYTES,
    MAX_FILES,
    MAX_TOTAL_PAGES,
    LoadedDocument,
    LoadResult,
    PageText,
    PdfLoadError,
    load_pdf,
    load_pdfs,
)

AMOSTRAS = Path(__file__).resolve().parent.parent / "docs" / "amostras"

REGULAMENTO = "regulamento_condominio.pdf"
ATA = "ata_assembleia_2026.pdf"
AVISO = "aviso_com_pagina_em_branco.pdf"
DIGITALIZADO = "digitalizado_sem_texto.pdf"


# ---------------------------------------------------------------- utilitários


def amostra(nome: str) -> bytes:
    return (AMOSTRAS / nome).read_bytes()


def pdf_com_texto(paginas: int, prefixo: str = "Pagina") -> bytes:
    """PDF gerado em memória com `fpdf2`, uma linha de texto por página."""
    pdf = FPDF()
    pdf.set_font("helvetica", size=12)
    for i in range(1, paginas + 1):
        pdf.add_page()
        pdf.cell(0, 10, f"{prefixo} {i} com texto extraivel.")
    return bytes(pdf.output())


def pdf_em_bytes(writer: PdfWriter) -> bytes:
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def pdf_com_senha(user_password: str, owner_password: str | None = None) -> bytes:
    writer = PdfWriter(clone_from=io.BytesIO(amostra(REGULAMENTO)))
    writer.encrypt(user_password=user_password, owner_password=owner_password)
    return pdf_em_bytes(writer)


def texto_pypdf(nome: str) -> list[str]:
    """Texto de cada página como o próprio pypdf devolve (referência sem normalização)."""
    return [p.extract_text() or "" for p in PdfReader(AMOSTRAS / nome).pages]


def cita_10_mb(mensagem: str) -> bool:
    return re.search(r"10\s*MB", mensagem, flags=re.IGNORECASE) is not None


# ---------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def regulamento() -> LoadedDocument:
    return load_pdf(amostra(REGULAMENTO), REGULAMENTO)


@pytest.fixture(scope="module")
def ata() -> LoadedDocument:
    return load_pdf(amostra(ATA), ATA)


@pytest.fixture(scope="module")
def aviso() -> LoadedDocument:
    return load_pdf(amostra(AVISO), AVISO)


# ---------------------------------------------------------------- constantes


def test_constantes_publicas_seguem_o_contrato():
    assert MAX_FILES == 3
    assert MAX_FILE_BYTES == 10 * 1024 * 1024
    assert MAX_TOTAL_PAGES == 100


def test_pdf_load_error_e_uma_exception():
    assert issubclass(PdfLoadError, Exception)


# ---------------------------------------------------------------- load_pdf: amostras reais


def test_regulamento_tem_6_paginas_em_base_1(regulamento):
    assert isinstance(regulamento, LoadedDocument)
    assert regulamento.source_name == REGULAMENTO
    assert regulamento.page_count == 6
    assert [p.page_number for p in regulamento.pages] == [1, 2, 3, 4, 5, 6]
    assert regulamento.empty_pages == ()
    assert all(isinstance(p, PageText) for p in regulamento.pages)
    assert all(p.source_name == REGULAMENTO for p in regulamento.pages)


def test_regulamento_quantidade_de_caracteres_por_pagina(regulamento):
    assert [len(p.text) for p in regulamento.pages] == [612, 502, 1349, 454, 352, 991]


def test_regulamento_fatos_na_pagina_certa(regulamento):
    por_pagina = {p.page_number: p.text for p in regulamento.pages}
    assert "48 unidades" in por_pagina[1]
    assert "Marta Figueiredo" in por_pagina[1]
    assert "48 unidades" not in por_pagina[2]
    assert "R$ 80,00" in por_pagina[3]  # churrasqueira
    assert "R$ 150,00" in por_pagina[3]  # salão de festas


def test_ata_fatos_na_pagina_certa(ata):
    assert ata.page_count == 2
    assert [p.page_number for p in ata.pages] == [1, 2]
    p1, p2 = ata.pages
    assert "R$ 680,00" in p1.text
    assert "R$ 680,00" not in p2.text
    assert "R$ 42.000,00" in p2.text
    assert "21h10" in p2.text


def test_aviso_ignora_pagina_2_em_branco(aviso):
    assert aviso.page_count == 3
    assert aviso.empty_pages == (2,)
    assert [p.page_number for p in aviso.pages] == [1, 3]
    assert "Bloco B" in aviso.pages[0].text
    assert "escadas" in aviso.pages[1].text


def test_digitalizado_sem_texto_e_recusado_citando_ocr():
    with pytest.raises(PdfLoadError) as erro:
        load_pdf(amostra(DIGITALIZADO), DIGITALIZADO)
    mensagem = str(erro.value)
    assert DIGITALIZADO in mensagem
    assert "OCR" in mensagem
    assert "digitaliz" in mensagem.lower() or "imagem" in mensagem.lower()


# ---------------------------------------------------------------- texto sem normalização


@pytest.mark.parametrize("nome", [REGULAMENTO, ATA, AVISO])
def test_texto_e_identico_ao_devolvido_pelo_pypdf(nome):
    documento = load_pdf(amostra(nome), nome)
    referencia = texto_pypdf(nome)
    for pagina in documento.pages:
        assert pagina.text == referencia[pagina.page_number - 1]


def test_texto_preserva_quebras_de_linha_originais(aviso):
    # O pypdf devolve "\n" no meio do texto do aviso; sem normalização, elas ficam.
    assert "\n" in aviso.pages[0].text


# ---------------------------------------------------------------- nome-base do arquivo


@pytest.mark.parametrize(
    "nome_recebido",
    [
        "pasta/sub/ata_assembleia_2026.pdf",
        "C:\\Users\\alguem\\Downloads\\ata_assembleia_2026.pdf",
        "pasta\\misturada/ata_assembleia_2026.pdf",
        "ata_assembleia_2026.pdf",
    ],
)
def test_source_name_e_reduzido_ao_nome_base(nome_recebido):
    documento = load_pdf(amostra(ATA), nome_recebido)
    assert documento.source_name == ATA
    assert all(p.source_name == ATA for p in documento.pages)


@pytest.mark.parametrize("nome_recebido", ["", "pasta/", "pasta\\"])
def test_nome_vazio_depois_do_nome_base_e_recusado(nome_recebido):
    with pytest.raises(PdfLoadError):
        load_pdf(amostra(ATA), nome_recebido)


def test_mensagem_de_erro_usa_o_nome_base():
    with pytest.raises(PdfLoadError) as erro:
        load_pdf(b"isto nao e um pdf", "pasta/sub\\quebrado.pdf")
    assert "quebrado.pdf" in str(erro.value)
    assert "pasta" not in str(erro.value)


# ---------------------------------------------------------------- tamanho e conteúdo inválido


def test_dados_vazios_sao_recusados_com_o_nome():
    with pytest.raises(PdfLoadError) as erro:
        load_pdf(b"", "relatorio.pdf")
    # A mensagem deve ser a de arquivo vazio, e não a genérica de PDF ilegível.
    assert "relatorio.pdf" in str(erro.value)
    assert "vazio" in str(erro.value)


def test_arquivo_acima_de_10_mb_e_recusado_citando_o_limite():
    # Um PDF válido com enchimento no final ainda abre no pypdf; só o tamanho o recusa.
    dados = amostra(ATA)
    dados += b"\n" * (MAX_FILE_BYTES + 1 - len(dados))
    assert len(dados) == MAX_FILE_BYTES + 1
    with pytest.raises(PdfLoadError) as erro:
        load_pdf(dados, "grande.pdf")
    assert "grande.pdf" in str(erro.value)
    assert cita_10_mb(str(erro.value))


def test_limite_de_tamanho_e_checado_antes_de_abrir_o_pdf(monkeypatch):
    aberturas = []
    init_original = PdfReader.__init__

    def init_espiao(self, *args, **kwargs):
        aberturas.append(True)
        init_original(self, *args, **kwargs)

    monkeypatch.setattr(pypdf.PdfReader, "__init__", init_espiao)
    dados = b"x" * (MAX_FILE_BYTES + 1)  # nem é PDF: a mensagem deve ser a do tamanho
    with pytest.raises(PdfLoadError) as erro:
        load_pdf(dados, "grande.pdf")
    assert cita_10_mb(str(erro.value))
    assert aberturas == []


def test_arquivo_com_exatamente_10_mb_e_aceito():
    dados = amostra(ATA)
    dados += b"\n" * (MAX_FILE_BYTES - len(dados))
    assert len(dados) == MAX_FILE_BYTES
    documento = load_pdf(dados, ATA)
    assert documento.page_count == 2


@pytest.mark.parametrize(
    "dados",
    [
        b"isto nao e um pdf",
        b"%PDF-1.4\n",
        b"\x00" * 1024,
        b"%PDF-1.7\n" + b"\xff\xfe lixo binario " * 50,
    ],
    ids=["texto", "so-cabecalho", "zeros", "cabecalho-com-lixo"],
)
def test_bytes_invalidos_viram_pdf_load_error(dados):
    with pytest.raises(PdfLoadError) as erro:
        load_pdf(dados, "invalido.pdf")
    assert "invalido.pdf" in str(erro.value)


@pytest.mark.parametrize("fracao", [0.02, 0.5, 0.99])
def test_pdf_truncado_vira_pdf_load_error(fracao):
    dados = amostra(REGULAMENTO)
    truncado = dados[: int(len(dados) * fracao)]
    with pytest.raises(PdfLoadError) as erro:
        load_pdf(truncado, "truncado.pdf")
    assert "truncado.pdf" in str(erro.value)


# ---------------------------------------------------------------- senha


def test_pdf_com_senha_e_recusado_citando_senha():
    with pytest.raises(PdfLoadError) as erro:
        load_pdf(pdf_com_senha("segredo"), "protegido.pdf")
    mensagem = str(erro.value)
    assert "protegido.pdf" in mensagem
    assert "senha" in mensagem.lower()


def test_pdf_criptografado_que_abre_com_senha_vazia_e_aceito():
    documento = load_pdf(pdf_com_senha("", owner_password="dono"), "so_dono.pdf")
    assert documento.page_count == 6
    assert "48 unidades" in documento.pages[0].text


# ---------------------------------------------------------------- quantidade de páginas


def test_pdf_com_zero_paginas_e_recusado():
    dados = pdf_em_bytes(PdfWriter())
    assert len(PdfReader(io.BytesIO(dados)).pages) == 0  # pré-condição do teste
    with pytest.raises(PdfLoadError) as erro:
        load_pdf(dados, "sem_paginas.pdf")
    assert "sem_paginas.pdf" in str(erro.value)


def test_pdf_com_mais_de_100_paginas_e_recusado():
    writer = PdfWriter(clone_from=io.BytesIO(pdf_com_texto(1)))
    for _ in range(MAX_TOTAL_PAGES):
        writer.add_blank_page(width=200, height=200)
    dados = pdf_em_bytes(writer)
    assert len(PdfReader(io.BytesIO(dados)).pages) == MAX_TOTAL_PAGES + 1
    with pytest.raises(PdfLoadError) as erro:
        load_pdf(dados, "longo.pdf")
    assert "longo.pdf" in str(erro.value)


def test_pdf_com_exatamente_100_paginas_e_aceito():
    documento = load_pdf(pdf_com_texto(MAX_TOTAL_PAGES), "cem.pdf")
    assert documento.page_count == MAX_TOTAL_PAGES
    assert [p.page_number for p in documento.pages] == list(range(1, 101))


def test_paginas_em_branco_geradas_contam_no_total_e_ficam_em_empty_pages():
    writer = PdfWriter(clone_from=io.BytesIO(pdf_com_texto(2)))
    writer.add_blank_page(width=200, height=200)
    documento = load_pdf(pdf_em_bytes(writer), "misto.pdf")
    assert documento.page_count == 3
    assert documento.empty_pages == (3,)
    assert [p.page_number for p in documento.pages] == [1, 2]


# ---------------------------------------------------------------- falha isolada de extração


def test_falha_ao_extrair_uma_pagina_conta_como_vazia(monkeypatch):
    extract_original = pypdf.PageObject.extract_text

    def extract_que_falha_na_pagina_2(self, *args, **kwargs):
        texto = extract_original(self, *args, **kwargs)
        if "(continuação)" in texto:  # só a página 2 da ata tem esse título
            raise RuntimeError("falha simulada na extração")
        return texto

    monkeypatch.setattr(pypdf.PageObject, "extract_text", extract_que_falha_na_pagina_2)
    documento = load_pdf(amostra(ATA), ATA)
    assert documento.page_count == 2
    assert documento.empty_pages == (2,)
    assert [p.page_number for p in documento.pages] == [1]
    assert "R$ 680,00" in documento.pages[0].text


# ---------------------------------------------------------------- imutabilidade


def test_page_text_e_imutavel(regulamento):
    pagina = regulamento.pages[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        pagina.text = "alterado"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        pagina.page_number = 99  # type: ignore[misc]


def test_loaded_document_e_load_result_sao_imutaveis(regulamento):
    with pytest.raises(dataclasses.FrozenInstanceError):
        regulamento.page_count = 1  # type: ignore[misc]
    resultado = load_pdfs([(ATA, amostra(ATA))])
    with pytest.raises(dataclasses.FrozenInstanceError):
        resultado.errors = ("x",)  # type: ignore[misc]


def test_colecoes_sao_tuplas(aviso):
    assert isinstance(aviso.pages, tuple)
    assert isinstance(aviso.empty_pages, tuple)
    resultado = load_pdfs([(AVISO, amostra(AVISO))])
    assert isinstance(resultado.documents, tuple)
    assert isinstance(resultado.errors, tuple)
    assert isinstance(resultado.warnings, tuple)
    assert isinstance(resultado.pages, tuple)


# ---------------------------------------------------------------- load_pdfs: problemas do conjunto


def test_load_pdfs_lista_vazia_levanta_erro():
    with pytest.raises(PdfLoadError):
        load_pdfs([])


def test_load_pdfs_mais_de_3_arquivos_levanta_erro_antes_de_processar():
    # Bytes inválidos: se processasse, viraria `errors`, e não exceção.
    arquivos = [(f"arquivo{i}.pdf", b"invalido") for i in range(MAX_FILES + 1)]
    with pytest.raises(PdfLoadError):
        load_pdfs(arquivos)


def test_load_pdfs_tres_arquivos_e_permitido():
    resultado = load_pdfs(
        [(REGULAMENTO, amostra(REGULAMENTO)), (ATA, amostra(ATA)), (AVISO, amostra(AVISO))]
    )
    assert len(resultado.documents) == 3
    assert resultado.errors == ()


@pytest.mark.parametrize(
    "nomes",
    [
        ("ata.pdf", "ata.pdf"),
        ("ata.pdf", "ATA.PDF"),
        ("pasta1/Ata.pdf", "pasta2\\aTa.pdf"),
    ],
)
def test_load_pdfs_nomes_duplicados_sem_diferenciar_maiusculas_levanta_erro(nomes):
    arquivos = [(nome, b"invalido") for nome in nomes]
    with pytest.raises(PdfLoadError):
        load_pdfs(arquivos)


# ---------------------------------------------------------------- load_pdfs: por arquivo


def test_load_pdfs_arquivo_com_erro_nao_derruba_os_demais():
    resultado = load_pdfs(
        [
            (REGULAMENTO, amostra(REGULAMENTO)),
            ("pasta/quebrado.pdf", b"isto nao e um pdf"),
            (ATA, amostra(ATA)),
        ]
    )
    assert isinstance(resultado, LoadResult)
    assert [d.source_name for d in resultado.documents] == [REGULAMENTO, ATA]
    assert len(resultado.errors) == 1
    assert resultado.errors[0].startswith("quebrado.pdf")


def test_load_pdfs_um_erro_por_arquivo_recusado_comecando_pelo_nome():
    resultado = load_pdfs(
        [
            (ATA, amostra(ATA)),
            (DIGITALIZADO, amostra(DIGITALIZADO)),
            ("protegido.pdf", pdf_com_senha("segredo")),
        ]
    )
    assert [d.source_name for d in resultado.documents] == [ATA]
    assert len(resultado.errors) == 2
    assert any(e.startswith(DIGITALIZADO) and "OCR" in e for e in resultado.errors)
    assert any(
        e.startswith("protegido.pdf") and "senha" in e.lower() for e in resultado.errors
    )


def test_load_pdfs_nenhum_aceito_devolve_resultado_sem_excecao():
    resultado = load_pdfs(
        [("a.pdf", b""), ("b.pdf", b"lixo"), (DIGITALIZADO, amostra(DIGITALIZADO))]
    )
    assert resultado.documents == ()
    assert resultado.pages == ()
    assert len(resultado.errors) == 3
    for nome in ("a.pdf", "b.pdf", DIGITALIZADO):
        assert any(e.startswith(nome) for e in resultado.errors)


def test_load_pdfs_aviso_de_paginas_vazias():
    resultado = load_pdfs([(AVISO, amostra(AVISO)), (ATA, amostra(ATA))])
    assert resultado.errors == ()
    assert len(resultado.warnings) == 1
    aviso = resultado.warnings[0]
    assert aviso.startswith(AVISO)
    assert re.search(r"\b2\b", aviso)


def test_load_pdfs_sem_paginas_vazias_nao_gera_aviso():
    resultado = load_pdfs([(REGULAMENTO, amostra(REGULAMENTO)), (ATA, amostra(ATA))])
    assert resultado.warnings == ()


def test_load_pdfs_soma_acima_de_100_paginas_levanta_erro():
    arquivos = [(f"parte{i}.pdf", pdf_com_texto(40, prefixo=f"Parte {i}")) for i in (1, 2, 3)]
    with pytest.raises(PdfLoadError) as erro:
        load_pdfs(arquivos)
    assert "100" in str(erro.value)


def test_load_pdfs_soma_de_exatamente_100_paginas_e_aceita():
    resultado = load_pdfs(
        [("parte1.pdf", pdf_com_texto(50)), ("parte2.pdf", pdf_com_texto(50))]
    )
    assert sum(d.page_count for d in resultado.documents) == 100


def test_load_pdfs_soma_considera_so_os_aceitos():
    # 60 + 60 passaria do limite, mas o segundo arquivo é recusado por outro motivo.
    arquivos = [
        ("parte1.pdf", pdf_com_texto(60)),
        ("parte2.pdf", pdf_com_texto(60)[:200]),  # truncado
    ]
    resultado = load_pdfs(arquivos)
    assert [d.source_name for d in resultado.documents] == ["parte1.pdf"]
    assert len(resultado.errors) == 1


def test_load_pdfs_soma_usa_page_count_com_paginas_vazias():
    # 99 páginas com texto + 1 com texto e 1 em branco = 101 páginas no total.
    writer = PdfWriter(clone_from=io.BytesIO(pdf_com_texto(1)))
    writer.add_blank_page(width=200, height=200)
    arquivos = [("longo.pdf", pdf_com_texto(99)), ("curto.pdf", pdf_em_bytes(writer))]
    with pytest.raises(PdfLoadError) as erro:
        load_pdfs(arquivos)
    assert "100" in str(erro.value)


def test_load_pdfs_preserva_ordem_de_entrada():
    resultado = load_pdfs(
        [(ATA, amostra(ATA)), (AVISO, amostra(AVISO)), (REGULAMENTO, amostra(REGULAMENTO))]
    )
    assert [d.source_name for d in resultado.documents] == [ATA, AVISO, REGULAMENTO]


def test_load_pdfs_propriedade_pages_concatena_na_ordem_de_entrada():
    resultado = load_pdfs(
        [(AVISO, amostra(AVISO)), (ATA, amostra(ATA)), ("pasta\\ruim.pdf", b"lixo")]
    )
    assert [(p.source_name, p.page_number) for p in resultado.pages] == [
        (AVISO, 1),
        (AVISO, 3),
        (ATA, 1),
        (ATA, 2),
    ]
    esperado = tuple(p for d in resultado.documents for p in d.pages)
    assert resultado.pages == esperado


def test_load_pdfs_reduz_nomes_ao_nome_base():
    resultado = load_pdfs([("docs/amostras/" + ATA, amostra(ATA))])
    assert resultado.documents[0].source_name == ATA
    assert all(p.source_name == ATA for p in resultado.pages)


# ---------------------------------------------------------------- lacunas apontadas na revisão (mutação)


def test_texto_da_pagina_nao_sofre_strip(monkeypatch):
    # A T03 depende do texto bruto; espaços nas pontas devem chegar intactos.
    monkeypatch.setattr(pypdf.PageObject, "extract_text", lambda self, *a, **k: "  texto \n")
    documento = load_pdf(amostra(ATA), ATA)
    assert all(p.text == "  texto \n" for p in documento.pages)


def test_espacos_nas_pontas_do_nome_sao_removidos():
    assert load_pdf(amostra(ATA), "  ata.pdf ").source_name == "ata.pdf"
    with pytest.raises(PdfLoadError):
        load_pdf(amostra(ATA), "   ")


def test_load_pdfs_nome_com_espacos_conta_como_duplicado():
    with pytest.raises(PdfLoadError):
        load_pdfs([("a.pdf", amostra(ATA)), (" a.pdf", amostra(REGULAMENTO))])


def test_falha_ao_contar_paginas_vira_pdf_load_error(monkeypatch):
    def pages_quebrado(self):
        raise pypdf.errors.PdfReadError("xref quebrada")

    monkeypatch.setattr(PdfReader, "pages", property(pages_quebrado))
    with pytest.raises(PdfLoadError) as erro:
        load_pdf(amostra(ATA), ATA)
    assert ATA in str(erro.value)


def _pdf_criptografado_com_senha_vazia() -> bytes:
    writer = PdfWriter(clone_from=io.BytesIO(amostra(ATA)))
    writer.encrypt(user_password="", owner_password="dono")
    return pdf_em_bytes(writer)


def test_falta_de_biblioteca_de_criptografia_vira_mensagem_clara(monkeypatch):
    def decrypt_sem_biblioteca(self, senha):
        raise pypdf.errors.DependencyError("cryptography ausente")

    monkeypatch.setattr(PdfReader, "decrypt", decrypt_sem_biblioteca)
    with pytest.raises(PdfLoadError) as erro:
        load_pdf(_pdf_criptografado_com_senha_vazia(), "protegido.pdf")
    mensagem = str(erro.value)
    assert "protegido.pdf" in mensagem
    assert "proteção" in mensagem
    assert "senha" not in mensagem


def test_erro_inesperado_ao_desbloquear_vira_pdf_load_error(monkeypatch):
    def decrypt_com_erro(self, senha):
        raise ValueError("falha interna")

    monkeypatch.setattr(PdfReader, "decrypt", decrypt_com_erro)
    with pytest.raises(PdfLoadError) as erro:
        load_pdf(_pdf_criptografado_com_senha_vazia(), "protegido.pdf")
    assert "protegido.pdf" in str(erro.value)


def test_load_pdfs_soma_estourada_informa_paginas_por_arquivo():
    arquivos = [(f"parte{i}.pdf", pdf_com_texto(40)) for i in range(1, 4)]
    with pytest.raises(PdfLoadError) as erro:
        load_pdfs(arquivos)
    assert "parte1.pdf: 40" in str(erro.value)
