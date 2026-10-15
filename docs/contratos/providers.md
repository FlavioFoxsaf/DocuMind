# Contrato — modelos locais (`src/config.py`, `src/ollama_client.py`, `src/providers.py`)

Criado na T12 (migração para o Ollama) e simplificado na T13 (27/09/2026), quando o Gemini
foi **removido**. Testes: `tests/test_config.py`, `tests/test_local_backend.py`,
`tests/test_app_local.py`, `tests/test_app.py` e, com o Ollama real instalado,
`tests/test_integration_ollama.py`.

## Regra central

Embeddings e geração rodam **nesta máquina**, no Ollama, sem chave e sem serviço externo.
A URL do Ollama só aceita `localhost`, `127.0.0.1` ou `::1`. Se o Ollama estiver desligado
ou faltar um modelo, o app mostra a instrução de correção e para; nada é baixado sozinho.
Vetores de modelos de embedding diferentes nunca se misturam no mesmo índice.

## Configuração (`load_settings`)

| Variável | Padrão | Observação |
|---|---|---|
| `OLLAMA_MODEL` | `qwen3:14b` | modelo de geração (T13: escolhido por precisão; `qwen3:8b` é a opção leve) |
| `OLLAMA_EMBEDDING_MODEL` | `qwen3-embedding:0.6b` | o mesmo modelo para trechos e perguntas |
| `DOCUMIND_OLLAMA_URL` | `http://127.0.0.1:11434` | só endereços locais; outro host gera `ConfigError` |
| `DOCUMIND_OLLAMA_TIMEOUT` | `180` | segundos, maior que zero |
| `DOCUMIND_OLLAMA_THINK` | `true` | raciocínio do Qwen3 antes da resposta |

`Settings(model, embedding_model, ollama_url, timeout, think)`, imutável. Variáveis antigas
(`GEMINI_*`, `DOCUMIND_PROVIDER`) que sobrarem num `.env` são ignoradas.

## `OllamaClient` (HTTP com `httpx`)

- `list_models()` → `GET /api/tags` (3 s de conexão).
- `embed(model, texts)` → `POST /api/embed` com `{"model", "input": [...]}`; devolve `embeddings`.
- `chat(model, prompt, schema, options, think)` → `POST /api/chat` com `stream: false`,
  `format: <JSON Schema>`, `think` e `options`.
- Erros viram `OllamaError` com instrução: conexão recusada (abrir o app Ollama ou
  `ollama serve`), HTTP 404 (`ollama pull <modelo>`), timeout (`DOCUMIND_OLLAMA_TIMEOUT`),
  outro HTTP ≥ 400 e corpo que não é JSON. `close()` e uso com `with`.
- `missing_models(client, nomes)`: nomes ausentes em `/api/tags` (`x` casa com `x:latest`).

## Adaptadores

- `OllamaEmbedder(client, model, batch_size=32)` (`src/retrieval.py`): lotes em ordem; as
  perguntas recebem `OLLAMA_QUERY_INSTRUCTION` na frente (formato do Qwen3-Embedding);
  checa contagem, dimensões iguais, `None` e NaN/inf; `OllamaError` → `RetrievalError`.
  `identity = "ollama:<modelo>"`.
- `OllamaGenerator(client, model, options=None, think=True)` (`src/answering.py`): o prompt,
  o `_RESPONSE_SCHEMA`, o parser, a recusa e a validação de citações são os de
  `answering.py`. Lê `message.content` e descarta `message.thinking`;
  `done_reason == "length"` → "incompleta"; conteúdo vazio → `AnsweringError`;
  `OllamaError` → `AnsweringError`.
- **Opções de amostragem (T13):** recomendação oficial do Qwen3. Com raciocínio,
  `OLLAMA_OPTIONS_THINK = {temperature 0.6, top_p 0.95, top_k 20, min_p 0, seed 42,
  num_ctx 8192, num_predict 4096}`; sem raciocínio, `OLLAMA_OPTIONS_NO_THINK = {temperature
  0.7, top_p 0.8, top_k 20, min_p 0, seed 42, num_ctx 8192, num_predict 1024}`. **Não usar
  `temperature 0` com raciocínio:** num teste de 27/09 o modelo entrou em repetição até o
  timeout de 180 s. A `seed` fixa mantém a resposta repetível na mesma máquina, e o
  `num_predict` transforma um eventual laço num erro controlado.
- `answer_question(question, index, embedder, generator, *, top_k, min_score,
  previous_question)`: o gerador segue o protocolo `Generator.generate(prompt) -> str`.

## Identidade do embedding

`build_index` grava a `identity` do embedder em `VectorIndex.embedder_id`; `retrieve`
levanta `RetrievalError` se o embedder da pergunta tiver outra identidade, mesmo com a mesma
dimensão. O app compara a identidade a cada execução e descarta índice e conversa quando o
modelo de embedding muda.

## `src/providers.py`

- `build_backend(settings, *, ollama_client=None) -> Backend(embedder, generator, label,
  privacy_note)`.
- `check_local_ready(settings, client=None)`: `ProviderError` se o Ollama não responde ou
  se falta um dos dois modelos (com o comando `ollama pull`). O app chama a cada execução e
  fecha a conexão depois.
