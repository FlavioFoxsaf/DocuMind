# Contrato de interface — `src/chunking.py` (T03)

Definido pelo integrador em 27/09/2026. A implementação e os testes
(`tests/test_chunking.py`) são escritos por responsáveis diferentes, seguindo **somente**
este contrato.

## Responsabilidade

Receber as páginas extraídas pelo loader (`src.loader.PageText`), aplicar uma
normalização leve e dividir cada página em trechos (`Chunk`) com sobreposição. **Nenhum
trecho atravessa páginas**, para que a citação "arquivo, página" seja sempre exata. O
módulo não usa rede, não grava em disco e não depende do Gemini.

## API pública

```python
DEFAULT_CHUNK_SIZE = 1000   # caracteres, máximo por trecho
DEFAULT_OVERLAP = 150       # caracteres de sobreposição desejados entre trechos vizinhos

@dataclass(frozen=True)
class Chunk:
    chunk_id: str       # ex.: "S1-P3-C2" (arquivo 1, página 3, trecho 2 da página)
    source_name: str
    page_number: int    # base 1, copiado do PageText
    text: str           # texto normalizado do trecho

def normalize_text(text: str) -> str: ...
def split_spans(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE,
                overlap: int = DEFAULT_OVERLAP) -> list[tuple[int, int]]: ...
def chunk_pages(pages: Sequence[PageText], chunk_size: int = DEFAULT_CHUNK_SIZE,
                overlap: int = DEFAULT_OVERLAP) -> tuple[Chunk, ...]: ...
```

## `normalize_text`

Aplica, nesta ordem:

1. Normalização Unicode **NFC**, para que letras acentuadas decompostas virem um único
   caractere.
2. Troca de caracteres de controle (categoria Unicode `Cc`, o que inclui `\x00`) por
   espaço.
3. Colapso de qualquer sequência de espaço em branco (`\s+`, incluindo `\n`, `\t` e
   espaço não separável `\xa0`) em um único espaço.
4. `strip()` nas pontas.

Não junta palavras hifenizadas, não muda maiúsculas e minúsculas, não remove pontuação
nem acentos. Motivo: "segunda-\nfeira" precisa continuar com hífen, e o texto citado deve
continuar conferível contra o PDF.

## `split_spans`

Devolve intervalos `(inicio, fim)` no estilo fatia Python (`text[inicio:fim]`) que dividem
`text`. `text` é o texto já normalizado.

- `chunk_size < 1` ou `overlap < 0` ou `overlap >= chunk_size` → `ValueError`.
- `text == ""` → `[]`.
- `len(text) <= chunk_size` → `[(0, len(text))]`.
- Invariantes para qualquer texto não vazio:
  1. O primeiro início é 0 e o último fim é `len(text)`.
  2. `0 < fim - inicio <= chunk_size` em todo intervalo.
  3. Os inícios são estritamente crescentes, e o mesmo vale para os fins.
  4. **Cobertura sem buracos:** cada intervalo começa em ou antes do fim do anterior
     (`inicio[i+1] <= fim[i]`).
  5. Com `overlap > 0`, intervalos vizinhos se sobrepõem (`inicio[i+1] < fim[i]`) sempre
     que isso não violar os invariantes 2–3. A sobreposição nunca passa de `overlap`
     caracteres.
- **Corte preferencial (qualidade, não invariante estrito):** quando o texto não termina
  dentro da janela `[inicio, inicio + chunk_size]`, o fim é escolhido nesta ordem:
  1. logo após o último fim de frase (`.`, `!`, `?` ou `;` seguido de espaço) que esteja
     na segunda metade da janela;
  2. senão, no último espaço da janela;
  3. senão, corte seco em `inicio + chunk_size`.

  O próximo início fica em `fim - overlap`, avançado até o começo da próxima palavra
  (logo após um espaço) se cair no meio de uma. Se esse ajuste não deixar
  sobreposição, o início fica em `fim - overlap` mesmo.
- Os trechos não começam nem terminam com espaço, exceto no caso de corte seco.

## `chunk_pages`

- Valida `chunk_size`/`overlap` como `split_spans`, mesmo com `pages` vazio.
- Processa as páginas na ordem recebida. Para cada página, normaliza o texto; páginas que
  ficam vazias depois disso são puladas, sem erro.
- Numeração do arquivo `S<n>`: `n` é a ordem de **primeira aparição** do `source_name`
  em `pages`, começando em 1. Um mesmo arquivo mantém o mesmo `n` em todas as páginas.
- `C<k>`: posição do trecho dentro da página, começando em 1.
- `chunk_id = f"S{n}-P{page_number}-C{k}"`. Os IDs são únicos na saída e iguais para a
  mesma entrada, então a função é determinística.
- `chunk.text == normalize_text(page.text)[inicio:fim]` para cada intervalo de
  `split_spans`, sem strip adicional.
- `source_name` e `page_number` são copiados do `PageText`.
- Devolve uma tupla na ordem página → trecho. `pages` vazio → `()`.

## Expectativa com as amostras (padrões 1000/150)

| Documento | Trechos esperados |
|---|---|
| `regulamento_condominio.pdf` | 7: página 3 com 2 trechos (S?-P3-C1 e C2), demais com 1 |
| `ata_assembleia_2026.pdf` | 2 |
| `aviso_com_pagina_em_branco.pdf` | 2 (páginas 1 e 3; a 2 já vem excluída pelo loader) |

Os testes podem carregar as amostras com `src.loader.load_pdf` (módulo já pronto e
testado) e montar `PageText` à mão para os casos sintéticos.

## Decisões da revisão (27/09/2026)

Estas decisões prevalecem sobre o texto acima quando houver diferença.

- **Pisos de progresso** (implementam os invariantes 3 e 4):
  - Os cortes preferenciais só valem se `fim > fim_anterior`; se não houver candidato, o
    corte é seco.
  - O próximo início é `max(fim - overlap, inicio + 1)`, depois avançado até o começo da
    palavra seguinte, desde que continue antes de `fim`.
- **Limites exatos:**
  - Um fim de frase vale quando `inicio + chunk_size // 2 <= fim <= inicio + chunk_size`,
    com `fim` logo após a pontuação e `text[fim] == " "`.
  - Um espaço na posição `p` vale quando `fim_anterior < p <= inicio + chunk_size`
    (janela fechada), e então `fim = p`.
- **Exceções à regra "não começa com espaço":**
  - corte seco;
  - `overlap = 0` com corte em espaço, em que o trecho seguinte começa pelo espaço do corte;
  - depois de um trecho de 1 caractere, que não tem sobreposição.
- **`S<n>`:** o número é dado pela primeira aparição em `pages`, mesmo que todas as
  páginas do arquivo acabem puladas. Buracos na numeração não afetam as citações.
- **Página repetida:** um par `(source_name, page_number)` repetido em `pages` gera
  `ValueError`, porque IDs duplicados quebrariam a validação de citações da T05.
- **Limitações declaradas:**
  - Abreviações como "Art. 13." contam como fim de frase. O efeito é cosmético, porque a
    sobreposição repete o cabeçalho no trecho seguinte.
  - Um corte seco pode partir um grafema composto (emoji com ZWJ), o que é irrelevante
    para PDFs de texto.
  - Um `overlap` acima de `chunk_size / 2` multiplica os trechos e o custo de embeddings.
    Os valores padrão (1000/150) ficam longe disso.
