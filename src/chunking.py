"""Normalização leve do texto e divisão de cada página em trechos com sobreposição."""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from src.loader import PageText

DEFAULT_CHUNK_SIZE = 1000  # caracteres, máximo por trecho
DEFAULT_OVERLAP = 150  # caracteres de sobreposição desejados entre trechos vizinhos

SENTENCE_ENDS = ".!?;"  # pontuação que, seguida de espaço, encerra uma frase

_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str  # ex.: "S1-P3-C2" (arquivo 1, página 3, trecho 2 da página)
    source_name: str
    page_number: int  # base 1, copiado do PageText
    text: str  # texto normalizado do trecho


def normalize_text(text: str) -> str:
    """Unifica acentos (NFC), troca controles por espaço e colapsa espaços em branco."""
    text = unicodedata.normalize("NFC", text)
    text = "".join(" " if unicodedata.category(ch) == "Cc" else ch for ch in text)
    return _WHITESPACE.sub(" ", text).strip()


def _validate(chunk_size: int, overlap: int) -> None:
    if chunk_size < 1:
        raise ValueError(f"chunk_size deve ser pelo menos 1 (recebido {chunk_size}).")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            f"overlap deve estar entre 0 e chunk_size - 1 (recebido {overlap}, "
            f"chunk_size {chunk_size})."
        )


def _find_end(text: str, start: int, chunk_size: int, min_end: int) -> int:
    """Escolhe onde termina o trecho que começa em start, sabendo que o texto continua.

    O fim fica sempre em [min_end, start + chunk_size]. min_end é o fim do trecho
    anterior + 1: sem esse piso, uma palavra longa depois do último corte faria o
    trecho novo terminar no mesmo espaço que o anterior, e o laço não avançaria.
    """
    limit = start + chunk_size  # fim máximo; text[limit] existe porque o texto continua

    # 1) Fim de frase na segunda metade da janela: o trecho fica com sentido completo.
    #    Só na segunda metade para não gerar trechos curtos demais.
    #    rfind procura "pontuação + espaço" com a pontuação em [lowest - 1, limit - 1];
    #    o fim é logo após a pontuação, então o espaço fica de fora do trecho.
    lowest = max(start + chunk_size // 2, min_end)
    sentence_end = max(text.rfind(mark + " ", lowest - 1, limit + 1) for mark in SENTENCE_ENDS)
    if sentence_end != -1:
        return sentence_end + 1

    # 2) Último espaço da janela: não corta palavra ao meio. O fim é a posição do
    #    espaço, então o trecho não termina com espaço.
    space = text.rfind(" ", min_end, limit + 1)
    if space != -1:
        return space

    # 3) Sem espaço útil (ex.: palavra maior que a janela): corte seco no limite.
    return limit


def _next_start(text: str, start: int, end: int, overlap: int) -> int:
    """Calcula o início do próximo trecho, recuando overlap caracteres a partir do fim."""
    # Nunca volta até o início atual: garante inícios estritamente crescentes (e o
    # avanço do laço) mesmo quando o corte na frase deixou o trecho curto.
    candidate = max(end - overlap, start + 1)

    # Se caiu no meio de uma palavra (ou num espaço), avança até logo após o próximo
    # espaço, para o trecho começar numa palavra inteira.
    position = candidate
    while position < end and text[position - 1] != " ":
        position += 1
    if position < end:
        return position

    # O ajuste consumiria toda a sobreposição: fica com o recuo exato, que ainda
    # repete o fim do trecho anterior (melhor meia palavra repetida que contexto perdido).
    return candidate


def split_spans(
    text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP
) -> list[tuple[int, int]]:
    """Divide o texto normalizado em intervalos (inicio, fim) com sobreposição."""
    _validate(chunk_size, overlap)
    spans: list[tuple[int, int]] = []
    start = 0
    previous_end = 0
    # A cada volta, o início cresce pelo menos 1 (_next_start), então o laço termina.
    while start < len(text):
        if len(text) - start <= chunk_size:
            spans.append((start, len(text)))  # o resto cabe inteiro: último trecho
            break
        end = _find_end(text, start, chunk_size, min_end=previous_end + 1)
        spans.append((start, end))
        start = _next_start(text, start, end, overlap)
        previous_end = end
    return spans


def chunk_pages(
    pages: Sequence[PageText],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> tuple[Chunk, ...]:
    """Gera os trechos de cada página, sem atravessar páginas, com IDs S<n>-P<p>-C<k>."""
    _validate(chunk_size, overlap)
    source_numbers: dict[str, int] = {}  # source_name -> n, na ordem de primeira aparição
    seen_pages: set[tuple[str, int]] = set()
    chunks: list[Chunk] = []
    for page in pages:
        # Página repetida geraria IDs repetidos e quebraria a validação de citações.
        key = (page.source_name, page.page_number)
        if key in seen_pages:
            raise ValueError(f"Página repetida na entrada: {page.source_name}, p. {page.page_number}.")
        seen_pages.add(key)
        source_number = source_numbers.setdefault(page.source_name, len(source_numbers) + 1)
        text = normalize_text(page.text)
        spans = split_spans(text, chunk_size, overlap)  # página vazia -> [] (pulada)
        for index, (start, end) in enumerate(spans, start=1):
            chunks.append(
                Chunk(
                    chunk_id=f"S{source_number}-P{page.page_number}-C{index}",
                    source_name=page.source_name,
                    page_number=page.page_number,
                    text=text[start:end],
                )
            )
    return tuple(chunks)
