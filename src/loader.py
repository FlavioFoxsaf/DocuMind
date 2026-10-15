"""Validação de PDFs recebidos como bytes e extração do texto por página."""

import io
from collections.abc import Sequence
from dataclasses import dataclass

from pypdf import PdfReader
from pypdf.errors import DependencyError

MAX_FILES = 3
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB por arquivo
MAX_TOTAL_PAGES = 100  # soma das páginas dos documentos aceitos


class PdfLoadError(Exception):
    """Erro com mensagem pronta para o usuário (str(erro))."""


@dataclass(frozen=True)
class PageText:
    source_name: str
    page_number: int  # base 1, igual ao número da página no leitor de PDF
    text: str  # texto extraído pelo pypdf, sem normalização


@dataclass(frozen=True)
class LoadedDocument:
    source_name: str
    page_count: int  # total de páginas do PDF, com as vazias
    pages: tuple[PageText, ...]  # apenas páginas com texto, em ordem crescente
    empty_pages: tuple[int, ...]  # páginas (base 1) sem texto extraível


@dataclass(frozen=True)
class LoadResult:
    documents: tuple[LoadedDocument, ...]  # na ordem de entrada, só os aceitos
    errors: tuple[str, ...]  # um por arquivo recusado; começa com o nome do arquivo
    warnings: tuple[str, ...]  # ex.: páginas vazias; começa com o nome do arquivo

    @property
    def pages(self) -> tuple[PageText, ...]:
        """Todas as páginas com texto dos documentos aceitos, na ordem de entrada."""
        return tuple(page for document in self.documents for page in document.pages)


def _base_name(source_name: str) -> str:
    """Remove os diretórios e os espaços nas pontas do nome, aceitando / e \\."""
    return source_name.replace("\\", "/").split("/")[-1].strip()


def _unreadable(name: str) -> PdfLoadError:
    return PdfLoadError(
        f"{name}: o arquivo não é um PDF legível (inválido, corrompido ou incompleto)."
    )


def _open_reader(data: bytes, name: str) -> PdfReader:
    """Abre o PDF em memória e desbloqueia os protegidos por senha vazia."""
    try:
        reader = PdfReader(io.BytesIO(data))
        encrypted = reader.is_encrypted
    except Exception as error:
        raise _unreadable(name) from error

    if encrypted:
        try:
            # decrypt devolve PasswordType.NOT_DECRYPTED (valor 0) quando a senha falha.
            unlocked = reader.decrypt("")
        except DependencyError as error:
            # AES exige o pacote "cryptography"; sem ele, o PDF não pode ser aberto.
            raise PdfLoadError(
                f"{name}: o PDF tem uma proteção que o app não consegue abrir. "
                "Salve uma cópia sem proteção e envie de novo."
            ) from error
        except Exception as error:
            raise PdfLoadError(f"{name}: o PDF é protegido por senha.") from error
        if not unlocked:
            raise PdfLoadError(f"{name}: o PDF é protegido por senha.")

    return reader


def _page_text(reader: PdfReader, index: int) -> str:
    """Extrai o texto de uma página; uma falha isolada conta como página vazia."""
    try:
        return reader.pages[index].extract_text() or ""
    except Exception:
        return ""


def load_pdf(data: bytes, source_name: str) -> LoadedDocument:
    """Valida um PDF e devolve o texto de cada página com o nome e a página em base 1."""
    name = _base_name(source_name)
    if not name:
        raise PdfLoadError("Arquivo sem nome: não é possível identificar o documento.")
    if not data:
        raise PdfLoadError(f"{name}: o arquivo está vazio.")
    # O tamanho é conferido antes de abrir o PDF, para não processar arquivos grandes.
    if len(data) > MAX_FILE_BYTES:
        raise PdfLoadError(f"{name}: o arquivo passa do limite de 10 MB.")

    reader = _open_reader(data, name)
    try:
        page_count = len(reader.pages)
    except Exception as error:
        raise _unreadable(name) from error

    if page_count == 0:
        raise PdfLoadError(f"{name}: o PDF não tem páginas.")
    if page_count > MAX_TOTAL_PAGES:
        raise PdfLoadError(
            f"{name}: o PDF tem {page_count} páginas e o limite é de "
            f"{MAX_TOTAL_PAGES} páginas."
        )

    pages: list[PageText] = []
    empty_pages: list[int] = []
    for page_number in range(1, page_count + 1):
        text = _page_text(reader, page_number - 1)
        if text.strip():
            pages.append(PageText(source_name=name, page_number=page_number, text=text))
        else:
            empty_pages.append(page_number)

    if not pages:
        raise PdfLoadError(
            f"{name}: nenhuma página tem texto extraível. O arquivo parece digitalizado "
            "ou ser só imagem, e esta versão não faz OCR."
        )

    return LoadedDocument(
        source_name=name,
        page_count=page_count,
        pages=tuple(pages),
        empty_pages=tuple(empty_pages),
    )


def load_pdfs(files: Sequence[tuple[str, bytes]]) -> LoadResult:
    """Carrega de 1 a 3 PDFs; erros de um arquivo não impedem os demais."""
    if not files:
        raise PdfLoadError("Nenhum arquivo foi enviado.")
    if len(files) > MAX_FILES:
        raise PdfLoadError(
            f"Foram enviados {len(files)} arquivos; o limite é de {MAX_FILES} PDFs por vez."
        )

    # Nomes repetidos tornariam as citações ambíguas ("regulamento.pdf, p. 2" de qual?).
    seen: set[str] = set()
    for source_name, _ in files:
        name = _base_name(source_name)
        if name and name.lower() in seen:
            raise PdfLoadError(
                f"{name}: há mais de um arquivo com esse nome. Renomeie um deles."
            )
        seen.add(name.lower())

    documents: list[LoadedDocument] = []
    errors: list[str] = []
    warnings: list[str] = []
    for source_name, data in files:
        try:
            document = load_pdf(data, source_name)
        except PdfLoadError as error:
            errors.append(str(error))
            continue
        documents.append(document)
        if document.empty_pages:
            numbers = ", ".join(str(number) for number in document.empty_pages)
            warnings.append(
                f"{document.source_name}: página(s) {numbers} sem texto foram ignoradas."
            )

    total_pages = sum(document.page_count for document in documents)
    if total_pages > MAX_TOTAL_PAGES:
        # A contagem por arquivo ajuda o usuário a decidir qual remover.
        detail = ", ".join(f"{d.source_name}: {d.page_count}" for d in documents)
        raise PdfLoadError(
            f"Os arquivos somam {total_pages} páginas ({detail}); o limite é de "
            f"{MAX_TOTAL_PAGES} páginas no conjunto."
        )

    return LoadResult(
        documents=tuple(documents),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
