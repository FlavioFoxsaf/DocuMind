"""Embeddings dos trechos (Ollama local) e busca por similaridade de cosseno em memória.

Ideia central: cada texto vira um vetor (embedding). Textos de sentido parecido geram
vetores que apontam para direções parecidas. O cosseno do ângulo entre dois vetores mede
isso: 1 = mesma direção, 0 = sem relação, -1 = direções opostas. Na prática, com
embeddings reais os scores ficam numa faixa estreita e positiva: o score serve para
ordenar trechos, não é uma probabilidade, e qualquer limiar precisa ser calibrado.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from src.chunking import Chunk
from src.ollama_client import OllamaError

DEFAULT_TOP_K = 4
OLLAMA_EMBED_BATCH_SIZE = 32  # textos por chamada ao Ollama local

# O Qwen3-Embedding trata pergunta e documento de formas diferentes: a pergunta leva uma
# instrução da tarefa na frente; o documento vai puro (formato da documentação do modelo).
# Uma pergunta curta ("qual a taxa?") e o trecho longo que a responde têm formas
# diferentes; indicar o papel de cada um deixa os dois vetores mais próximos quando combinam.
OLLAMA_QUERY_INSTRUCTION = (
    "Instruct: Given a question about the user's documents, retrieve the passages "
    "that answer it\nQuery: "
)


class RetrievalError(Exception):
    """Mensagem pronta para o usuário (pt-BR); nunca contém o texto do documento."""


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float  # similaridade de cosseno, em [-1, 1]


class Embedder(Protocol):
    # identity diz de qual modelo vieram os vetores (ex.: "ollama:qwen3-embedding:0.6b").
    # Vetores de modelos diferentes vivem em espaços diferentes e não podem ser comparados.
    identity: str

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray: ...  # (n, d)

    def embed_query(self, text: str) -> np.ndarray: ...  # (d,)


class OllamaEmbedder:
    """Gera embeddings com o Ollama local; documentos e perguntas usam o mesmo modelo."""

    def __init__(self, client, model: str, batch_size: int = OLLAMA_EMBED_BATCH_SIZE):
        if batch_size < 1:
            raise ValueError("batch_size deve ser pelo menos 1.")
        self._client = client  # src.ollama_client.OllamaClient (ou um falso nos testes)
        self._model = model
        self._batch_size = batch_size
        self.identity = f"ollama:{model}"

    def __repr__(self) -> str:
        return f"OllamaEmbedder(model={self._model!r}, batch_size={self._batch_size})"

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            vectors = self._client.embed(self._model, texts)
        except OllamaError as error:
            raise RetrievalError(str(error)) from error
        if not isinstance(vectors, list):
            raise RetrievalError("O Ollama devolveu uma resposta de embeddings incompleta.")
        _check_count(vectors, texts)
        return vectors

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        """Matriz float32 (n, d), uma linha por texto, na ordem recebida."""
        return _embed_in_batches(texts, self._batch_size, self._embed_batch)

    def embed_query(self, text: str) -> np.ndarray:
        """Vetor float32 (d,) da pergunta, com a instrução de busca na frente."""
        (vector,) = self._embed_batch([OLLAMA_QUERY_INSTRUCTION + text])
        return _to_array(vector)


def _check_count(vectors: list, texts: list[str]) -> None:
    if len(vectors) != len(texts):
        raise RetrievalError(f"O modelo devolveu {len(vectors)} embeddings para {len(texts)} textos.")


def _embed_in_batches(texts: Sequence[str], batch_size: int, embed_batch) -> np.ndarray:
    """Lotes de no máximo batch_size textos, um após o outro, para manter a ordem."""
    texts = list(texts)
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    vectors: list = []
    for start in range(0, len(texts), batch_size):
        vectors.extend(embed_batch(texts[start : start + batch_size]))
    try:
        sizes = {len(vector) for vector in vectors}
    except TypeError as error:  # ex.: um vetor None
        raise RetrievalError("O modelo devolveu uma resposta de embeddings incompleta.") from error
    if len(sizes) != 1:
        raise RetrievalError("O modelo devolveu embeddings de tamanhos diferentes.")
    return _to_array(vectors)


def _to_array(values) -> np.ndarray:
    """Converte a resposta do modelo em float32; valores ausentes ou inválidos viram erro."""
    try:
        # Atenção: o NumPy converte None em NaN sem reclamar; por isso a checagem abaixo.
        array = np.array(values, dtype=np.float32)
    except (TypeError, ValueError) as error:
        raise RetrievalError("O modelo devolveu uma resposta de embeddings incompleta.") from error
    _require_finite(array)
    return array


def _require_finite(array: np.ndarray) -> None:
    # NaN ou infinito estragariam os scores em silêncio: NaN < limiar é sempre False,
    # então uma recusa por score baixo nunca dispararia.
    if not np.isfinite(array).all():
        raise RetrievalError("Os embeddings vieram com valores inválidos (NaN ou infinito).")


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    """Divide cada linha pela sua norma L2 (comprimento), para que fique com norma 1.

    `keepdims=True` faz as normas saírem com formato (n, 1); pelo broadcasting do NumPy,
    a divisão (n, d) / (n, 1) divide cada linha pela própria norma. O cálculo é feito em
    float64 para não estourar com valores grandes. Linhas de norma zero continuam zero:
    dividir por zero geraria NaN.
    """
    matrix = matrix.astype(np.float64)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    safe_norms = np.where(norms > 0, norms, 1.0)
    return (matrix / safe_norms).astype(np.float32)


@dataclass(frozen=True, eq=False)
class VectorIndex:
    """Trechos e seus embeddings normalizados; a linha i da matriz é o trecho i."""

    chunks: tuple[Chunk, ...]
    matrix: np.ndarray  # (n, d), float32, linhas com norma L2 = 1 (ou zero)
    embedder_id: str | None = None  # identity do embedder que gerou a matriz

    def search(
        self, query_vector: np.ndarray, top_k: int = DEFAULT_TOP_K
    ) -> tuple[RetrievedChunk, ...]:
        """Os top_k trechos mais parecidos com a consulta, do maior score ao menor."""
        if top_k < 1:
            raise ValueError("top_k deve ser pelo menos 1.")

        query = np.asarray(query_vector, dtype=np.float32)
        dimension = self.matrix.shape[1]
        if query.shape != (dimension,):
            raise RetrievalError(
                f"O vetor da pergunta tem formato {query.shape}, mas o índice usa "
                f"vetores de tamanho {dimension}."
            )
        _require_finite(query)

        # Cosseno(a, b) = (a · b) / (|a| * |b|). Com a e b já de norma 1, o denominador é
        # 1 e o cosseno vira só o produto escalar. Como as linhas da matriz foram
        # normalizadas uma vez em build_index, basta normalizar a consulta e fazer um
        # único produto matriz × vetor para obter o cosseno com todos os trechos.
        norm = np.linalg.norm(query.astype(np.float64))
        if norm > 0:  # consulta de norma zero fica zero: score 0 para todos, sem NaN
            query = (query / norm).astype(np.float32)
        scores = self.matrix @ query  # (n,)
        # Arredondamentos de float32 podem dar 1.0000001; o cosseno fica em [-1, 1].
        scores = np.clip(scores, -1.0, 1.0)

        # argsort ordena do menor ao maior; com -scores, do maior ao menor. "stable"
        # mantém a ordem original do índice entre scores empatados.
        order = np.argsort(-scores, kind="stable")[:top_k]
        return tuple(
            RetrievedChunk(chunk=self.chunks[i], score=float(scores[i])) for i in order
        )


def build_index(chunks: Sequence[Chunk], embedder: Embedder) -> VectorIndex:
    """Gera os embeddings de todos os trechos e monta o índice normalizado."""
    chunks = tuple(chunks)
    if not chunks:
        raise RetrievalError("Não há nenhum trecho para indexar.")

    matrix = np.asarray(embedder.embed_documents([c.text for c in chunks]))
    if matrix.ndim != 2 or matrix.shape[0] != len(chunks) or matrix.shape[1] < 1:
        raise RetrievalError(
            f"Os embeddings vieram no formato {matrix.shape}; eram esperadas "
            f"{len(chunks)} linhas com pelo menos 1 coluna."
        )
    _require_finite(matrix)

    # Normalizar agora, uma vez só, deixa cada busca barata (só um produto escalar).
    normalized = _normalize_rows(matrix)
    normalized.setflags(write=False)  # o índice é imutável, inclusive a matriz
    return VectorIndex(
        chunks=chunks, matrix=normalized, embedder_id=getattr(embedder, "identity", None)
    )


def retrieve(
    index: VectorIndex, question: str, embedder: Embedder, top_k: int = DEFAULT_TOP_K
) -> tuple[RetrievedChunk, ...]:
    """Transforma a pergunta em vetor e busca os trechos mais próximos no índice."""
    question = question.strip()
    if not question:
        raise ValueError("A pergunta está vazia.")
    # Mesmo com a mesma dimensão, vetores de modelos diferentes não se comparam: a busca
    # devolveria trechos aleatórios sem nenhum erro visível. Por isso a checagem explícita.
    if index.embedder_id != getattr(embedder, "identity", None):
        raise RetrievalError(
            "Os documentos foram indexados com outro modelo de embedding. "
            "Clique em Processar documentos para reindexar."
        )
    return index.search(embedder.embed_query(question), top_k=top_k)
