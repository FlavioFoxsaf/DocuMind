"""Interface web do DocuMind. Execute com: streamlit run app.py

Este arquivo contém só a interface e o estado da sessão; a lógica fica em src/.
Os modelos rodam localmente no Ollama, sem chave e sem serviço externo.
Os nomes que os testes substituem (config.load_settings, providers.build_backend,
providers.check_local_ready, answering.answer_question...) são acessados pelo módulo, na
hora da chamada, para que o monkeypatch funcione.
"""

import logging
import re
from hashlib import sha256

import streamlit as st

from src import answering, chunking, config, loader, providers, retrieval


# --- Configuração e modelos ----------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def get_backend(settings):
    """Embedder e gerador locais, um por processo e por configuração.

    Só guarda o cliente HTTP do Ollama, sem dados do usuário (nunca o índice).
    """
    return providers.build_backend(settings)


def load_settings_or_stop():
    """Lê a configuração; com erro (ex.: URL fora da máquina), mostra e interrompe."""
    try:
        return config.load_settings()
    except config.ConfigError as error:
        st.error(md_escape(str(error)))  # a mensagem pode citar valores do .env
        st.caption("Depois de corrigir o `.env`, reinicie o app.")
        st.stop()


def check_ready_or_stop(settings) -> None:
    """Confere se o Ollama responde e se os modelos estão instalados; senão, para."""
    try:
        providers.check_local_ready(settings)
    except providers.ProviderError as error:
        st.error(md_escape(str(error)))  # nomes de modelo têm ":" "_" "." etc.
        st.caption(
            "O DocuMind usa modelos locais no Ollama. Depois de corrigir, recarregue a "
            "página. Veja a seção de instalação do README."
        )
        st.stop()


def init_state() -> None:
    """Cria as entradas da sessão na primeira execução."""
    defaults = {"index": None, "documents": [], "fingerprint": None, "messages": []}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_index() -> None:
    """Esquece o conjunto indexado e a conversa sobre ele."""
    st.session_state.index = None
    st.session_state.documents = []
    st.session_state.fingerprint = None
    st.session_state.messages = []


# --- Formatação ----------------------------------------------------------------------------


# Tudo o que vem de fora (nome de arquivo, texto do PDF, resposta do modelo) pode trazer
# Markdown. Sem escape, um PDF malicioso poderia induzir o modelo a responder com uma
# imagem externa (![x](https://...)), que o navegador baixaria sozinho: um canal de
# vazamento. HTML já é bloqueado pelo Streamlit (allow_html fica desligado).
_MD_ALL = re.compile(r"([\\`*_{}\[\]()#+\-.!|$<>~])")
_MD_ANSWER = re.compile(r"([\\$\[\]!<])")


def md_escape(text: str) -> str:
    """Texto literal: nomes de arquivo, IDs e mensagens que citam arquivos."""
    return _MD_ALL.sub(r"\\\1", text)


def md_answer(text: str) -> str:
    """Resposta do modelo: mantém negrito e listas, mas bloqueia links, imagens e LaTeX.

    O $ vira \\$ para que "R$ 50 ... R$ 80" não vire fórmula.
    """
    return _MD_ANSWER.sub(r"\\\1", text)


def fingerprint_of(uploads) -> tuple:
    """Identifica o conteúdo dos arquivos, inclusive substituições de mesmo tamanho."""
    return tuple(sorted((f.name, sha256(f.getvalue()).hexdigest()) for f in uploads))


def chunk_to_dict(item) -> dict:
    """RetrievedChunk → dict simples, guardado no histórico da sessão."""
    return {
        "chunk_id": item.chunk.chunk_id,
        "source_name": item.chunk.source_name,
        "page_number": item.chunk.page_number,
        "score": item.score,
        "text": item.chunk.text,
    }


def summarize_documents(documents, chunks) -> list[dict]:
    """Resumo de cada documento indexado, para a lista da barra lateral."""
    return [
        {
            "name": doc.source_name,
            "pages": doc.page_count,
            "empty_pages": len(doc.empty_pages),
            "chunks": sum(1 for c in chunks if c.source_name == doc.source_name),
        }
        for doc in documents
    ]


# --- Barra lateral -------------------------------------------------------------------------


def invalidate_if_changed(uploads, backend) -> None:
    """Se os arquivos ou o modelo de embedding mudaram, descarta índice e conversa.

    Vetores de modelos diferentes vivem em espaços diferentes: comparar a pergunta de um
    modelo com trechos de outro daria resultados sem sentido.
    """
    index = st.session_state.index
    if index is None:
        return
    if index.embedder_id != getattr(backend.embedder, "identity", None):
        reset_index()
        st.info("O modelo de embedding mudou. Clique em Processar para reindexar.")
    elif fingerprint_of(uploads) != st.session_state.fingerprint:
        reset_index()
        st.info("Os documentos mudaram. Clique em Processar para reindexar.")


def process_documents(uploads, backend) -> None:
    """Extrai, divide em trechos e indexa os PDFs enviados."""
    reset_index()  # uma falha deixa o índice vazio, sem misturar conjuntos
    try:
        with st.spinner("Lendo os PDFs..."):
            result = loader.load_pdfs([(f.name, f.getvalue()) for f in uploads])
    except loader.PdfLoadError as error:
        st.error(md_escape(str(error)))
        return
    # As mensagens do loader começam pelo nome do arquivo, que pode conter Markdown.
    for message in result.errors:
        st.error(md_escape(message))
    for message in result.warnings:
        st.warning(md_escape(message))
    if not result.documents:
        return

    chunks = chunking.chunk_pages(result.pages)
    try:
        with st.spinner("Indexando os trechos (embeddings)..."):
            index = retrieval.build_index(chunks, backend.embedder)
    except retrieval.RetrievalError as error:
        st.error(str(error))
        return

    st.session_state.index = index
    st.session_state.documents = summarize_documents(result.documents, chunks)
    st.session_state.fingerprint = fingerprint_of(uploads)
    st.session_state.messages = []
    st.success(f"{len(result.documents)} documento(s) indexado(s) em {len(chunks)} trechos.")


def render_documents() -> None:
    """Lista os documentos do índice atual."""
    st.subheader("Documentos ativos")
    if not st.session_state.documents:
        st.caption("Nenhum documento processado.")
        return
    for doc in st.session_state.documents:
        with_text = doc["pages"] - doc["empty_pages"]
        st.markdown(
            f"📄 **{md_escape(doc['name'])}**  \n"
            f"{with_text}/{doc['pages']} páginas com texto · {doc['chunks']} trechos"
        )


def render_sidebar(backend) -> None:
    with st.sidebar:
        st.header("Documentos")
        uploads = st.file_uploader(
            "Envie de 1 a 3 PDFs", type="pdf", accept_multiple_files=True
        ) or []
        st.caption(
            f"Até {loader.MAX_FILES} arquivos, {loader.MAX_FILE_BYTES // (1024 * 1024)} MB "
            f"cada e {loader.MAX_TOTAL_PAGES} páginas no total. Só PDF com texto "
            "selecionável (sem OCR)."
        )
        invalidate_if_changed(uploads, backend)

        if st.button("Processar documentos", type="primary", disabled=not uploads,
                     width="stretch"):
            process_documents(uploads, backend)

        st.divider()
        render_documents()

        # Sempre habilitado: a barra lateral é desenhada antes do chat, então um botão
        # dependente de "messages" ficaria desabilitado logo após a primeira resposta.
        if st.button("Limpar conversa", width="stretch"):
            st.session_state.messages = []

        st.divider()
        st.caption(f"Modelos: {md_escape(backend.label)}")
        st.caption(backend.privacy_note)


# --- Chat ----------------------------------------------------------------------------------


def render_chunk(item: dict) -> None:
    """Um trecho: arquivo, página, ID e score, e o texto sem interpretar Markdown."""
    st.caption(
        md_escape(
            f"{item['source_name']} — p. {item['page_number']} · ID {item['chunk_id']} · "
            f"score {item['score']:.3f}"
        )
    )
    st.text(item["text"])


def render_sources(sources: list[dict]) -> None:
    """Lista 'arquivo — p. N' sem repetir o par, e um expander por trecho citado."""
    pairs = dict.fromkeys((s["source_name"], s["page_number"]) for s in sources)
    lines = "\n".join(f"- {md_escape(name)} — p. {page}" for name, page in pairs)
    st.markdown(f"**Fontes**\n\n{lines}")
    for position, source in enumerate(sources):
        label = md_escape(
            f"{source['source_name']} — p. {source['page_number']} · trecho {source['chunk_id']}"
        )
        # O primeiro trecho citado já aparece aberto: a evidência fica visível sem clique.
        with st.expander(label, expanded=position == 0):
            render_chunk(source)


def render_context(context: list[dict]) -> None:
    with st.expander("Trechos consultados"):
        if not context:
            st.caption("Nenhum trecho foi recuperado.")
        for item in context:
            render_chunk(item)


def render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(md_escape(message["content"]))
            return
        if message.get("error"):
            st.error(message["content"])
            return

        if message["found"]:
            st.markdown(md_answer(message["content"]))
            render_sources(message["sources"])
        else:
            st.warning(message["content"])
        if message["invalid_citations"]:
            ids = ", ".join(message["invalid_citations"])
            st.caption(
                md_escape(f"O modelo citou fontes inexistentes, que foram descartadas: {ids}.")
            )
        render_context(message["context"])


def ask(question: str, previous_question, backend) -> dict:
    """Consulta os documentos e devolve a mensagem do assistente para o histórico."""
    try:
        with st.spinner("Buscando nos documentos e gerando a resposta..."):
            answer = answering.answer_question(
                question,
                st.session_state.index,
                backend.embedder,
                backend.generator,
                previous_question=previous_question,
            )
    except (retrieval.RetrievalError, answering.AnsweringError) as error:
        return {"role": "assistant", "content": str(error), "error": True}

    return {
        "role": "assistant",
        "content": answer.text,
        "found": answer.found,
        "sources": [chunk_to_dict(item) for item in answer.sources],
        "context": [chunk_to_dict(item) for item in answer.context],
        "invalid_citations": list(answer.invalid_citations),
        "error": False,
    }


def handle_question(question: str, backend) -> None:
    """Registra a pergunta, obtém a resposta e mostra as duas."""
    messages = st.session_state.messages
    previous = next((m["content"] for m in reversed(messages) if m["role"] == "user"), None)

    user_message = {"role": "user", "content": question}
    messages.append(user_message)
    render_message(user_message)

    reply = ask(question, previous, backend)
    messages.append(reply)
    render_message(reply)


def render_chat(backend) -> None:
    has_index = st.session_state.index is not None
    if not has_index:
        st.info("Envie de 1 a 3 PDFs na barra lateral e clique em **Processar documentos**.")
    else:
        st.caption(
            "As respostas podem conter erros: confira o trecho e a página citados. "
            "Não substitui análise jurídica ou profissional."
        )

    for message in st.session_state.messages:
        render_message(message)

    # max_chars evita mandar por engano um texto enorme para o modelo.
    question = st.chat_input(
        "Pergunte algo sobre os documentos", disabled=not has_index, max_chars=1000
    )
    if question and question.strip() and has_index:
        handle_question(question.strip(), backend)


# --- Script (roda de cima a baixo a cada interação) ---------------------------------------
# Como o Streamlit funciona aqui:
# - cada clique ou pergunta reexecuta este arquivo inteiro, de cima a baixo;
# - st.session_state sobrevive às reexecuções, mas é por sessão (aba do navegador): cada
#   usuário tem o próprio índice e a própria conversa, e recarregar a página zera tudo;
# - st.cache_resource é por processo e compartilhado entre sessões; por isso só os
#   clientes dos modelos (sem dados do usuário) ficam lá, nunca o índice.

st.set_page_config(page_title="DocuMind", page_icon="📄", layout="wide")
# Os avisos do pypdf podem conter fragmentos do PDF; ficam fora do terminal.
logging.getLogger("pypdf").setLevel(logging.ERROR)

st.title("📄 DocuMind")
st.caption("Pergunte sobre os seus PDFs e receba respostas com arquivo, página e trecho de origem.")

settings = load_settings_or_stop()
check_ready_or_stop(settings)
backend = get_backend(settings)
init_state()
render_sidebar(backend)
render_chat(backend)
