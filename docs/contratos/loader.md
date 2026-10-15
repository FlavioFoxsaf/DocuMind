# Contrato de interface — `src/loader.py` (T02)

Definido pelo integrador em 27/09/2026. A implementação (`src/loader.py`) e os testes
(`tests/test_loader.py`) são escritos por responsáveis diferentes e devem seguir
**somente** este contrato. Mudanças no contrato passam pelo integrador e são
registradas no `STATUS.md`.

## Responsabilidade

Validar arquivos PDF recebidos como bytes, extrair o texto **por página** com `pypdf`
e devolver o texto bruto com o nome do arquivo e o número da página em base 1. A
normalização do texto e a divisão em trechos ficam na T03 (`src/chunking.py`), fora
deste módulo.

O módulo não grava nada em disco, não usa rede e não registra em log o conteúdo dos
documentos. Todas as mensagens são em português do Brasil e servem para mostrar
diretamente ao usuário.

## API pública

```python
MAX_FILES = 3
MAX_FILE_BYTES = 10 * 1024 * 1024   # 10 MB por arquivo
MAX_TOTAL_PAGES = 100               # soma das páginas dos documentos aceitos

class PdfLoadError(Exception):
    """Erro com mensagem pronta para o usuário (str(erro))."""

@dataclass(frozen=True)
class PageText:
    source_name: str
    page_number: int   # base 1, igual ao número da página no leitor de PDF
    text: str          # texto extraído pelo pypdf, sem normalização

@dataclass(frozen=True)
class LoadedDocument:
    source_name: str
    page_count: int                 # total de páginas do PDF, com as vazias
    pages: tuple[PageText, ...]     # apenas páginas com texto, em ordem crescente
    empty_pages: tuple[int, ...]    # páginas (base 1) sem texto extraível

@dataclass(frozen=True)
class LoadResult:
    documents: tuple[LoadedDocument, ...]  # na ordem de entrada, só os aceitos
    errors: tuple[str, ...]      # um por arquivo recusado; começa com o nome do arquivo
    warnings: tuple[str, ...]    # ex.: páginas vazias; começa com o nome do arquivo

    @property
    def pages(self) -> tuple[PageText, ...]:
        """Todas as páginas com texto dos documentos aceitos, na ordem de entrada."""

def load_pdf(data: bytes, source_name: str) -> LoadedDocument: ...
def load_pdfs(files: Sequence[tuple[str, bytes]]) -> LoadResult: ...
```

## Regras de `load_pdf`

1. `source_name` é reduzido ao nome-base do arquivo (sem diretórios, aceitando `/` e
   `\`) e perde os espaços nas pontas. Um nome vazio depois disso gera `PdfLoadError`
   ("Arquivo sem nome: ..."; é a única mensagem que não começa pelo nome).
   *Revisão de 27/09:* o strip do nome foi incorporado ao contrato.
2. Levanta `PdfLoadError`, com o nome do arquivo na mensagem, quando:
   - `data` está vazio;
   - `len(data) > MAX_FILE_BYTES`. Essa checagem acontece **antes** de abrir o PDF, e a
     mensagem cita o limite de 10 MB;
   - o conteúdo não é um PDF legível (bytes inválidos, arquivo corrompido ou truncado).
     Nenhuma exceção do `pypdf` ou de outra biblioteca escapa; todas viram `PdfLoadError`;
   - o PDF é protegido por senha e não abre com senha vazia (mensagem cita "senha");
   - o PDF é criptografado e o ambiente não tem a biblioteca de criptografia. A mensagem
     fala em "proteção", não em "senha", e sugere enviar uma cópia sem proteção;
   - o PDF tem 0 páginas;
   - o PDF tem mais de `MAX_TOTAL_PAGES` páginas;
   - **nenhuma** página tem texto extraível. A mensagem explica que o arquivo parece
     digitalizado ou ser só imagem e cita OCR como limitação.
3. Uma página é vazia quando `(page.extract_text() or "").strip() == ""`. Uma falha ao
   extrair uma página isolada conta como página vazia e não derruba o documento. Páginas
   vazias vão para `empty_pages` e não aparecem em `pages`.
4. `PageText.text` guarda o texto como o `pypdf` devolveu, sem strip nem normalização.

## Regras de `load_pdfs`

1. Levanta `PdfLoadError` (problema do conjunto, antes de processar qualquer arquivo)
   quando:
   - a lista está vazia;
   - há mais de `MAX_FILES` arquivos;
   - dois arquivos têm o mesmo nome-base, sem diferenciar maiúsculas de minúsculas.
     Nomes repetidos tornariam as citações ambíguas.
2. Cada arquivo passa por `load_pdf`. Um `PdfLoadError` de um arquivo vira uma entrada em
   `errors`, e os demais continuam. Nenhum arquivo é descartado em silêncio.
3. Para cada documento aceito com `empty_pages`, gera um aviso em `warnings` com o nome do
   arquivo e as páginas ignoradas (ex.: `"aviso.pdf: página(s) 2 sem texto foram ignoradas."`).
4. Se a soma de `page_count` dos documentos aceitos passar de `MAX_TOTAL_PAGES`, levanta
   `PdfLoadError` citando o limite de 100 páginas e a contagem por arquivo
   (ex.: `a.pdf: 60, b.pdf: 60`). Os `errors`/`warnings` já apurados são descartados,
   porque o usuário precisa refazer a seleção de qualquer jeito.
5. Se nenhum documento for aceito, **não** levanta exceção: devolve `documents` vazio e
   `errors` preenchido. A interface decide o que mostrar.

## Amostras disponíveis (`docs/amostras/`, gabarito em `FATOS.md`)

| Arquivo | Páginas | Caracteres extraídos por página |
|---|---|---|
| `regulamento_condominio.pdf` | 6 | 612, 502, 1349, 454, 352, 991 |
| `ata_assembleia_2026.pdf` | 2 | 491, 476 |
| `aviso_com_pagina_em_branco.pdf` | 3 | 174, 0, 154 |
| `digitalizado_sem_texto.pdf` | 1 | 0 |

Os testes podem gerar PDFs extras em memória com `fpdf2` (dependência de dev) ou
`pypdf.PdfWriter` (páginas em branco, criptografia com senha). Não devem gravar fora de
`tmp_path`.
