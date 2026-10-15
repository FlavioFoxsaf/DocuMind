# Especificação — `app.py` (T06, interface Streamlit)

> **Atualização de 27/09/2026 (T13): o Gemini foi removido do projeto.** O DocuMind usa só o Ollama local. Trechos deste contrato que citam `GeminiEmbedder`, `GeminiGenerator`, `GEMINI_API_KEY`, `google-genai`, códigos HTTP da API do Google ou modelos `gemini-...` são **históricos** (T04–T06, T12) e não descrevem mais o código. O contrato vigente dos modelos está em [`providers.md`](providers.md).

Definida pelo integrador em 27/09/2026. O `app.py` contém **somente interface e estado da
sessão**. Toda a lógica fica em `src/`. Os módulos prontos são `loader`, `chunking`,
`config`, `retrieval` e `answering`; ver os contratos correspondentes.

## Inicialização

1. `st.set_page_config(page_title="DocuMind", page_icon="📄", layout="wide")`.
2. `logging.getLogger("pypdf").setLevel(logging.ERROR)`: privacidade e menos ruído, por
   decisão registrada na revisão da T02.
3. `load_settings()`. Se der `ConfigError`, mostra `st.error(str(erro))` com instrução
   curta (copiar `.env.example` para `.env` e preencher `GEMINI_API_KEY`) e chama
   `st.stop()`. A chave **nunca** aparece na tela.
4. O cliente `genai.Client(api_key=settings.api_key)` é criado com
   `@st.cache_resource`, uma vez por processo.

## Estado da sessão (`st.session_state`)

| Chave | Conteúdo |
|---|---|
| `index` | `VectorIndex` ou `None` |
| `documents` | resumo dos documentos indexados: nome, páginas, páginas vazias, trechos |
| `fingerprint` | identificação do conjunto indexado: tupla ordenada de `(nome, tamanho)` dos uploads |
| `messages` | lista de dicts: `role` (`"user"`/`"assistant"`), `content` e, para o assistente, `found`, `sources` (lista de dicts com `chunk_id`, `source_name`, `page_number`, `score` e `text`), `context` (igual), `invalid_citations`, `error` (bool) |

Nada é gravado em disco. Recarregar a página zera a sessão.

## Barra lateral: documentos

- `st.file_uploader("Envie de 1 a 3 PDFs", type="pdf", accept_multiple_files=True)`, com
  uma legenda que mostra os limites: 3 arquivos, 10 MB cada, 100 páginas no total, só PDF
  com texto selecionável (sem OCR).
- **Invalidação:** se o `fingerprint` atual dos uploads for diferente do indexado, e já
  houver um índice, apaga `index`, `documents` e `messages` e mostra
  `st.info("Os documentos mudaram. Clique em Processar para reindexar.")`. Remover todos os
  arquivos também invalida. Motivo: não misturar respostas de conjuntos diferentes.
- Botão **"Processar documentos"**, desabilitado sem arquivos. Ao clicar:
  1. `load_pdfs([(f.name, f.getvalue()) for f in uploads])`. Um `PdfLoadError` do conjunto
     vira `st.error`. Cada item de `errors` vira `st.error` e cada item de `warnings` vira
     `st.warning`.
  2. Se houver documentos aceitos: `chunk_pages(result.pages)` e depois `build_index`
     com `GeminiEmbedder(client, settings.embedding_model)`, dentro de
     `st.spinner("Gerando embeddings...")`. Um `RetrievalError` vira `st.error` e o
     índice fica `None`.
  3. Em caso de sucesso, grava `index`, `documents` e `fingerprint`, limpa `messages` e
     mostra `st.success` com o número de documentos e de trechos.
- **Lista de documentos ativos:** para cada documento indexado, mostra o nome, as páginas
  com texto sobre o total e o número de trechos.
- Botão **"Limpar conversa"**: limpa `messages` sem apagar o índice.
- Aviso fixo e curto de privacidade: os trechos são enviados à API do Gemini. Usar só
  documentos públicos ou autorizados.

## Área principal: chat

- Título e subtítulo de uma linha explicando o app.
- Sem índice: `st.info` pedindo para enviar e processar os PDFs. O `st.chat_input` fica
  desabilitado.
- Renderiza o histórico com `st.chat_message`.
- A cada nova pergunta:
  - `previous_question` = a última mensagem `user` do histórico, antes de adicionar a
    atual, ou `None`;
  - chama `answer_question(...)` com `settings.model` dentro de um `st.spinner`;
  - um `RetrievalError` ou `AnsweringError` vira uma mensagem do assistente com
    `error=True` e o texto do erro, exibida com `st.error`, **sem** fingir uma resposta;
  - outras exceções não são capturadas, para não esconder bugs.
- **Exibição de uma resposta:**
  - `found=True`: mostra o texto e depois **"Fontes"** como lista `arquivo — p. N`, sem
    repetir o par. Cada fonte tem um `st.expander` com o trecho citado (ID e score).
  - `found=False`: mostra o texto de recusa com `st.warning`.
  - Sempre há um `st.expander("Trechos consultados")` com todos os trechos do `context`,
    com arquivo, página, ID e score (3 casas).
  - Se houver `invalid_citations`, mostra uma nota discreta:
    "O modelo citou fontes inexistentes, que foram descartadas: ...".

## Testabilidade

- O código de UI pode ficar em funções pequenas dentro do `app.py`, mas o script precisa
  rodar de cima a baixo no `streamlit run app.py`.
- Os testes usam `streamlit.testing.v1.AppTest.from_file("app.py")`, com o Gemini
  substituído por monkeypatch:
  - `src.config.load_settings`, ou variáveis de ambiente;
  - `google.genai.Client`, `src.retrieval.GeminiEmbedder` e
    `src.answering.answer_question`, ou um cliente falso.

  Para que o monkeypatch funcione, o `app.py` deve **acessar esses nomes pelos módulos
  em tempo de execução**, com `from src import retrieval, answering, config` e depois
  `retrieval.GeminiEmbedder(...)`, e `from google import genai` com `genai.Client(...)`.
- `.streamlit/config.toml` com `server.maxUploadSize = 10` (MB), para o Streamlit recusar
  arquivos grandes antes de carregá-los na memória.

## Migração local (T12, 27/09/2026)

- Inicialização: `load_settings()` → `check_ready_or_stop(settings)` (no modo local, erro de
  Ollama desligado ou modelo ausente vira `st.error` com instrução e `st.stop()`, sem
  recorrer ao Gemini) → `get_backend(settings)` (`@st.cache_resource`, só clientes).
- A barra lateral mostra `backend.label` (provedor e modelos) e `backend.privacy_note`,
  que é diferente no modo local e no Gemini.
- `invalidate_if_changed(uploads, backend)` também descarta índice e conversa quando
  `index.embedder_id` difere do embedder atual (troca de provedor ou de modelo).
- `app.py` não importa `google.genai`; os testes do modo local estão em
  `tests/test_app_local.py` e os do modo gemini em `tests/test_app.py`.
