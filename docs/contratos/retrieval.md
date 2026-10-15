# Contrato de interface — `src/config.py` e `src/retrieval.py` (T04)

> **Atualização de 27/09/2026 (T13): o Gemini foi removido do projeto.** O DocuMind usa só o Ollama local. Trechos deste contrato que citam `GeminiEmbedder`, `GeminiGenerator`, `GEMINI_API_KEY`, `google-genai`, códigos HTTP da API do Google ou modelos `gemini-...` são **históricos** (T04–T06, T12) e não descrevem mais o código. O contrato vigente dos modelos está em [`providers.md`](providers.md).

Definido pelo integrador em 27/09/2026. A implementação e os testes
(`tests/test_config.py`, `tests/test_retrieval.py`) são escritos por responsáveis
diferentes, seguindo **somente** este contrato.

Dependência: `src.chunking.Chunk`, uma dataclass imutável com os campos `chunk_id`,
`source_name`, `page_number` e `text` (ver `docs/contratos/chunking.md`). Ela é
desenvolvida em paralelo; os testes só precisam construir `Chunk` com esses campos.

## `src/config.py` — configuração sem vazar segredo

```python
DEFAULT_MODEL = "gemini-3.6-flash"
DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"

class ConfigError(Exception):
    """Mensagem pronta para o usuário; nunca contém o valor da chave."""

@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)   # não aparece em repr/print/log
    model: str
    embedding_model: str

def load_settings(env: Mapping[str, str] | None = None) -> Settings: ...
```

- Com `env=None`, chama `dotenv.load_dotenv()` (sem sobrescrever variáveis já definidas)
  e lê `os.environ`. Com `env` informado, usa **apenas** esse mapeamento e não lê `.env`
  nem `os.environ`. Isso permite testar sem efeitos colaterais.
- `GEMINI_API_KEY` ausente, vazia ou só com espaços → `ConfigError`. A mensagem cita o
  nome da variável e o arquivo `.env`.
- `GEMINI_MODEL` e `GEMINI_EMBEDDING_MODEL` ausentes ou vazios → usam os padrões acima.
- Todos os valores passam por `strip()`.
- `repr(settings)` e `str(settings)` **não** contêm o valor da chave.

## `src/retrieval.py` — embeddings e busca em memória

```python
DEFAULT_TOP_K = 4
EMBED_BATCH_SIZE = 50   # textos por chamada à API

class RetrievalError(Exception):
    """Mensagem pronta para o usuário (pt-BR); nunca contém chave nem texto do documento."""

@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float        # similaridade de cosseno, em [-1, 1]

class Embedder(Protocol):
    def embed_documents(self, texts: Sequence[str]) -> np.ndarray: ...   # (n, d)
    def embed_query(self, text: str) -> np.ndarray: ...                  # (d,)

class GeminiEmbedder:
    def __init__(self, client, model: str, batch_size: int = EMBED_BATCH_SIZE): ...
    def embed_documents(self, texts: Sequence[str]) -> np.ndarray: ...
    def embed_query(self, text: str) -> np.ndarray: ...

class VectorIndex:
    chunks: tuple[Chunk, ...]
    matrix: np.ndarray          # (n, d), float32, linhas com norma L2 = 1 (ou zero)
    def search(self, query_vector: np.ndarray, top_k: int = DEFAULT_TOP_K
               ) -> tuple[RetrievedChunk, ...]: ...

def build_index(chunks: Sequence[Chunk], embedder: Embedder) -> VectorIndex: ...
def retrieve(index: VectorIndex, question: str, embedder: Embedder,
             top_k: int = DEFAULT_TOP_K) -> tuple[RetrievedChunk, ...]: ...
```

### `GeminiEmbedder`

- `client` é um `google.genai.Client` (ou um objeto falso com a mesma interface
  `client.models.embed_content(model=..., contents=[...], config=...)`). O embedder não
  cria o cliente nem lê a chave.
- `embed_documents`: envia os textos em lotes de no máximo `batch_size`, **na ordem**, com
  `config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")`. Junta
  `response.embeddings[i].values` numa matriz `float32 (n, d)`. Lista vazia → matriz
  `(0, 0)` sem chamar a API.
- `embed_query`: uma chamada com `task_type="RETRIEVAL_QUERY"` e `contents=[text]`;
  devolve um vetor `float32 (d,)`.
- Qualquer exceção do cliente vira `RetrievalError`, sem deixar escapar a exceção
  original como tipo, mas encadeada com `from`. Mensagens por código
  (`getattr(erro, "code", None)`):
  - 429: cota ou limite atingido; aguardar;
  - 401/403, ou 400 com "key" na mensagem: chave recusada, conferir `GEMINI_API_KEY`;
  - 404: modelo de embedding não encontrado, conferir `GEMINI_EMBEDDING_MODEL`;
  - 5xx: serviço instável, tentar de novo;
  - outros erros: falha genérica ao gerar embeddings, conferir a conexão.
- Resposta com número de embeddings diferente do número de textos enviados no lote, ou
  com vetores de tamanhos diferentes → `RetrievalError`.

### `build_index`

- `chunks` vazio → `RetrievalError` ("nenhum trecho para indexar").
- Chama `embedder.embed_documents([c.text for c in chunks])` **uma vez**.
- Matriz com formato diferente de `(len(chunks), d)`, com `d >= 1` → `RetrievalError`.
- Normaliza cada linha para norma L2 = 1. Uma linha de norma zero continua zero, sem NaN.
- `VectorIndex.chunks` é uma tupla na mesma ordem de `chunks`.

### `VectorIndex.search`

- `top_k < 1` → `ValueError`. Se `top_k` for maior que o número de trechos, devolve
  todos.
- Um `query_vector` com tamanho diferente de `d` → `RetrievalError`.
- Normaliza a consulta. Uma consulta de norma zero dá score 0 para todos, sem NaN.
- `score` = produto escalar entre vetores normalizados, ou seja, o cosseno. Convertido
  para `float` Python.
- Ordena por score decrescente. Em caso de empate, vale a ordem original do índice
  (ordenação estável).
- Nunca inventa trechos: cada `RetrievedChunk.chunk` é um objeto de `index.chunks`.

### `retrieve`

- `question.strip() == ""` → `ValueError`.
- Faz `embedder.embed_query(question.strip())` e depois `index.search(...)`.

## Fora do escopo desta tarefa

A decisão de recusa por limiar de score fica na T05 (`answering.py`), que recebe o
score. Não há cache em disco, FAISS nem persistência.

## Teste real opcional

`tests/test_integration_gemini.py`, marcado para ser **pulado** quando
`GEMINI_API_KEY` não estiver definido no ambiente. Ele confirma que `embed_query`
devolve um vetor `(d,)` e que, nas amostras, a pergunta "Qual o valor da taxa de reserva
da churrasqueira?" traz a página 3 do regulamento no top-4.

## Decisões da revisão (27/09/2026)

- Embeddings com NaN ou infinito, ou com um valor ausente (`None`, que o NumPy converteria
  em NaN), geram `RetrievalError`, tanto no embedder quanto em `build_index` e `search`.
  Um NaN faria `score < limiar` ser sempre falso e desligaria a recusa por score.
- A normalização é calculada em float64 e convertida para float32 no fim, para evitar
  overflow.
- `VectorIndex.matrix` é somente leitura (`setflags(write=False)`).
- `search` exige uma consulta com formato exatamente `(d,)`; `(1, d)` gera
  `RetrievalError`.
- Um erro 400 só é tratado como erro de chave se `error.message` contiver "api key" ou se
  `error.details` contiver "API_KEY". O texto inteiro do erro dava falso positivo.
- O teste de integração roda quando `GEMINI_API_KEY` está no ambiente **ou** no `.env`.
  O cliente usa novas tentativas (`HttpRetryOptions(attempts=4)`).
- Para a T06: nunca exibir `__cause__` nem traceback. O `APIError` original guarda headers
  com a chave e a resposta completa da API.

## Migração local (T12, 27/09/2026)

Ver `providers.md`. Resumo: `OllamaEmbedder` ao lado do `GeminiEmbedder`; o import do SDK
Gemini passou a ser tardio; `Embedder.identity` e `VectorIndex.embedder_id` impedem buscar
com um modelo diferente do que indexou. O `MIN_SCORE` **não** foi recalibrado para o
Ollama porque os scores locais não separam perguntas com e sem resposta (relatórios reais
de 27/09: sem resposta até 0,607; respondível a partir de 0,514).
