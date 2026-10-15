"""Avaliação da matriz de perguntas da T07 contra o pipeline real do DocuMind.

Uso (na raiz do projeto):

    .venv\\Scripts\\python docs\\avaliacao\\avaliar.py                          # dry-run offline
    .venv\\Scripts\\python docs\\avaliacao\\avaliar.py --real                   # Ollama local
    .venv\\Scripts\\python docs\\avaliacao\\avaliar.py --real --modelo qwen3:14b  # outro modelo
    .venv\\Scripts\\python docs\\avaliacao\\avaliar.py --real --sem-raciocinio   # think=false

O script usa o loader, o chunking, a busca e a geração reais de `src/`. Com --real, usa o
Ollama local com os modelos da configuração (.env ou padrões), que --modelo, --modelo-embedding
e --sem-raciocinio podem sobrescrever para comparar. No dry-run, o embedder e o gerador
são trocados por versões falsas: o objetivo é provar que o script roda de ponta a ponta,
não medir qualidade.

Para cada pergunta ele mede:
- recuperação: alguma evidência esperada (arquivo + página) está no top-k?
- citação: as fontes citadas incluem uma página esperada?
- termos-chave: a resposta contém os termos que uma resposta correta deve conter?
- recusa correta: recusou se e somente se `deve_recusar`?
- score do 1º trecho, score da melhor evidência esperada e tempo.

E grava um relatório Markdown em docs/avaliacao/resultados/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import statistics
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
sys.path.insert(0, str(RAIZ))  # permite "from src..." rodando o script de qualquer pasta

from src import answering  # noqa: E402
from src.answering import AnsweringError, answer_question  # noqa: E402
from src.chunking import chunk_pages  # noqa: E402
from src.loader import PdfLoadError, load_pdfs  # noqa: E402
from src.retrieval import RetrievalError, build_index, retrieve  # noqa: E402

MATRIZ = AQUI / "matriz.json"
RESULTADOS = AQUI / "resultados"
CAMPOS = ("id", "pergunta", "anterior", "tipo", "resposta_esperada", "evidencias",
          "deve_recusar", "termos_chave")


# --- Utilidades de texto ------------------------------------------------------------------


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos, sem espaços e sem ',00' ("R$ 80,00" casa com "R$80")."""
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\s+", "", texto)
    return texto.replace(",00", "")


def termo_presente(termo: str, texto: str) -> bool:
    """O termo aceita alternativas separadas por '|'; basta uma aparecer."""
    alvo = normalizar(texto)
    return any(normalizar(alt) in alvo for alt in termo.split("|") if alt.strip())


def resumir(texto: str, limite: int = 140) -> str:
    """Uma linha curta e segura para tabela Markdown."""
    texto = " ".join(texto.split()).replace("|", "\\|")
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


# --- Modo dry-run: embedder e cliente falsos -----------------------------------------------


class EmbedderSacoDePalavras:
    """Embedding local por contagem de palavras (hash em 512 posições). Só para o dry-run.

    Não tem nada de semântico: "churrasco" e "churrasqueira" são palavras diferentes.
    """

    DIM = 512

    def _vetor(self, texto: str) -> np.ndarray:
        vetor = np.zeros(self.DIM, dtype=np.float32)
        texto = unicodedata.normalize("NFD", texto.lower())
        texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
        for palavra in re.findall(r"\w+", texto):
            if len(palavra) < 3:  # ignora "de", "a", "o"... (stopwords baratas)
                continue
            posicao = int(hashlib.md5(palavra.encode()).hexdigest(), 16) % self.DIM
            vetor[posicao] += 1.0
        return vetor

    def embed_documents(self, texts):
        return np.stack([self._vetor(t) for t in texts])

    def embed_query(self, text):
        return self._vetor(text)


class _RespostaFalsa:
    def __init__(self, text: str):
        self.text = text


class _ModelosFalsos:
    """Responde sempre citando o 1º trecho do prompt, com o começo do texto dele."""

    _TRECHO = re.compile(r'<trecho id="([^"]+)"[^>]*>\n(.*?)\n</trecho>', re.DOTALL)

    def generate_content(self, model, contents, config=None):
        achado = self._TRECHO.search(contents)
        if not achado:
            return _RespostaFalsa(json.dumps({"status": "not_found", "answer": "", "citations": []}))
        trecho_id, texto = achado.groups()
        resposta = {"status": "answered", "answer": texto[:300], "citations": [trecho_id]}
        return _RespostaFalsa(json.dumps(resposta, ensure_ascii=False))


class GeradorFalso:
    """Gerador do dry-run: mesma interface dos geradores reais (generate(prompt) -> JSON)."""

    def __init__(self):
        self._modelos = _ModelosFalsos()

    def generate(self, prompt: str) -> str:
        return self._modelos.generate_content("falso", prompt).text


# --- Embedder que guarda o último vetor de consulta ---------------------------------------


class EmbedderComMemoria:
    """Repassa as chamadas e guarda o último vetor de pergunta.

    Assim dá para ordenar TODOS os trechos (e achar o score da evidência esperada mesmo
    fora do top-k) sem pagar uma segunda chamada de embedding à API.
    """

    def __init__(self, interno):
        self._interno = interno
        self.identity = getattr(interno, "identity", None)  # o índice guarda o modelo de origem
        self.ultima_consulta: np.ndarray | None = None

    def embed_documents(self, texts):
        return self._interno.embed_documents(texts)

    def embed_query(self, text):
        self.ultima_consulta = self._interno.embed_query(text)
        return self.ultima_consulta


# --- Matriz ----------------------------------------------------------------------------------


def carregar_matriz(caminho: Path) -> dict:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    ids = set()
    for item in dados["perguntas"]:
        faltando = [c for c in CAMPOS if c not in item]
        if faltando:
            raise SystemExit(f"Matriz inválida: {item.get('id')} sem os campos {faltando}.")
        if item["id"] in ids:
            raise SystemExit(f"Matriz inválida: id repetido {item['id']}.")
        ids.add(item["id"])
        if item["deve_recusar"] == bool(item["evidencias"]):
            raise SystemExit(
                f"Matriz inválida: {item['id']} precisa de evidências se, e só se, for respondível."
            )
    return dados


def conferir_matriz(perguntas: list[dict], paginas: dict[tuple[str, int], str]) -> list[str]:
    """Confere a matriz contra o texto real: páginas existem e cada termo aparece nelas."""
    avisos = []
    for item in perguntas:
        textos = []
        for ev in item["evidencias"]:
            chave = (ev["arquivo"], ev["pagina"])
            if chave not in paginas:
                avisos.append(f"{item['id']}: {ev['arquivo']} p. {ev['pagina']} não existe.")
            else:
                textos.append(paginas[chave])
        junto = " ".join(textos)
        for termo in item["termos_chave"]:
            if junto and not termo_presente(termo, junto):
                avisos.append(f"{item['id']}: termo '{termo}' não aparece nas páginas esperadas.")
    return avisos


# --- Execução ---------------------------------------------------------------------------------


@dataclass
class Resultado:
    item: dict
    repeticao: int
    resposta: str = ""
    encontrou: bool = False
    motivo_recusa: str | None = None
    erro: str | None = None
    paginas_contexto: list[str] = field(default_factory=list)
    paginas_citadas: list[str] = field(default_factory=list)
    recuperou: bool | None = None  # alguma evidência no top-k (None = não se aplica)
    recuperou_todas: bool | None = None
    posicao_evidencia: int | None = None  # posição (1 = melhor) da 1ª evidência no ranking total
    citou_certo: bool | None = None
    termos_faltando: list[str] = field(default_factory=list)
    recusa_correta: bool | None = None
    score_top1: float | None = None
    score_evidencia: float | None = None
    tempo: float = 0.0
    controle: dict | None = None  # a mesma busca sem a pergunta anterior

    @property
    def respondivel(self) -> bool:
        return not self.item["deve_recusar"]

    @property
    def termos_ok(self) -> bool | None:
        if not self.respondivel or self.erro:
            return None
        return self.encontrou and not self.termos_faltando

    @property
    def ok(self) -> bool:
        if self.erro:
            return False
        if not self.respondivel:
            return bool(self.recusa_correta)
        return bool(self.recusa_correta and self.recuperou and self.citou_certo and self.termos_ok)


def rotulo(arquivo: str, pagina: int) -> str:
    return f"{arquivo} p.{pagina}"


def posicao_e_score(index, vetor, esperadas: set[tuple[str, int]]):
    """Ordena todos os trechos pela consulta; devolve (posição, score) da melhor evidência."""
    ranking = index.search(vetor, top_k=len(index.chunks))
    for posicao, item in enumerate(ranking, start=1):
        if (item.chunk.source_name, item.chunk.page_number) in esperadas:
            return posicao, item.score
    return None, None


def avaliar_pergunta(item, repeticao, index, embedder, gerador, args) -> Resultado:
    r = Resultado(item=item, repeticao=repeticao)
    esperadas = {(e["arquivo"], e["pagina"]) for e in item["evidencias"]}
    inicio = time.perf_counter()
    try:
        resposta = answer_question(
            item["pergunta"], index, embedder, gerador,
            top_k=args.top_k, min_score=args.min_score, previous_question=item["anterior"],
        )
    except (RetrievalError, AnsweringError) as erro:
        # Mensagens do projeto: já vêm em pt-BR e nunca contêm a chave.
        r.tempo = time.perf_counter() - inicio
        r.erro = str(erro)
        return r
    r.tempo = time.perf_counter() - inicio

    r.resposta = resposta.text
    r.encontrou = resposta.found
    r.motivo_recusa = resposta.refusal_reason
    r.paginas_contexto = [rotulo(c.chunk.source_name, c.chunk.page_number) for c in resposta.context]
    citadas = {(c.chunk.source_name, c.chunk.page_number) for c in resposta.sources}
    r.paginas_citadas = sorted(rotulo(a, p) for a, p in citadas)
    r.score_top1 = resposta.context[0].score if resposta.context else None
    r.recusa_correta = (not resposta.found) == item["deve_recusar"]

    if r.respondivel:
        no_topk = {(c.chunk.source_name, c.chunk.page_number) for c in resposta.context}
        r.recuperou = bool(no_topk & esperadas)
        r.recuperou_todas = esperadas <= no_topk
        r.citou_certo = bool(citadas & esperadas)
        r.termos_faltando = [t for t in item["termos_chave"] if not termo_presente(t, resposta.text)]
        if embedder.ultima_consulta is not None:
            r.posicao_evidencia, r.score_evidencia = posicao_e_score(
                index, embedder.ultima_consulta, esperadas
            )

    # Controle de contaminação: a mesma pergunta, buscada SEM a anterior (só busca, sem LLM).
    if item["anterior"] and r.respondivel:
        try:
            sozinha = retrieve(index, item["pergunta"], embedder, args.top_k)
            posicao, score = posicao_e_score(index, embedder.ultima_consulta, esperadas)
            r.controle = {
                "score_top1": sozinha[0].score,
                "recuperou": any(
                    (c.chunk.source_name, c.chunk.page_number) in esperadas for c in sozinha
                ),
                "posicao_evidencia": posicao,
                "score_evidencia": score,
            }
        except RetrievalError as erro:
            r.controle = {"erro": str(erro)}
    return r


# --- Métricas e relatório -------------------------------------------------------------------


def taxa(valores: list[bool]) -> str:
    if not valores:
        return "—"
    acertos = sum(1 for v in valores if v)
    return f"{acertos}/{len(valores)} ({100 * acertos / len(valores):.0f}%)"


def fmt(valor, casas: int = 3) -> str:
    return "—" if valor is None else f"{valor:.{casas}f}"


def sim_nao(valor) -> str:
    return "—" if valor is None else ("sim" if valor else "NÃO")


def distribuicao(valores: list[float]) -> str:
    if not valores:
        return "—"
    return (f"n={len(valores)}, mín {min(valores):.3f}, mediana {statistics.median(valores):.3f}, "
            f"máx {max(valores):.3f}")


def calcular_metricas(resultados: list[Resultado]) -> dict:
    validos = [r for r in resultados if not r.erro]
    resp = [r for r in validos if r.respondivel]
    sem = [r for r in validos if not r.respondivel]
    top1_resp = [r.score_top1 for r in resp if r.score_top1 is not None]
    top1_sem = [r.score_top1 for r in sem if r.score_top1 is not None]
    m = {
        "total": len(resultados),
        "erros": len(resultados) - len(validos),
        "ok": taxa([r.ok for r in resultados]),
        "recuperacao": taxa([r.recuperou for r in resp]),
        "recuperacao_todas": taxa([r.recuperou_todas for r in resp]),
        "citacao": taxa([r.citou_certo for r in resp]),
        "termos": taxa([r.termos_ok for r in resp]),
        "recusa_sem_resposta": taxa([not r.encontrou for r in sem]),
        "falsa_recusa": taxa([not r.encontrou for r in resp]),
        "top1_resp": distribuicao(top1_resp),
        "top1_sem": distribuicao(top1_sem),
    }
    if top1_resp:
        # Recusa por score acontece quando top1 < MIN_SCORE. Logo, o maior limiar que não
        # recusa nenhuma respondível é o menor top-1 entre elas (arredondado para baixo).
        limiar = np.floor(min(top1_resp) * 1000) / 1000
        m["min_score_max"] = limiar
        if top1_sem:
            margem = limiar - max(top1_sem)
            m["margem"] = margem
            if margem > 0:
                m["sugestao"] = (
                    f"Os scores separam as duas classes nesta matriz. Qualquer MIN_SCORE em "
                    f"({max(top1_sem):.3f}, {limiar:.3f}] recusaria todas as sem resposta sem recusar "
                    f"respondíveis; um valor prudente é o ponto médio, {(limiar + max(top1_sem)) / 2:.3f}. "
                    f"Margem de apenas {margem:.3f} com {len(top1_resp) + len(top1_sem)} medições: "
                    "confirme com mais perguntas antes de fixar."
                )
            else:
                m["sugestao"] = (
                    f"Os scores NÃO separam as classes (a sem resposta mais alta, {max(top1_sem):.3f}, "
                    f"passa a respondível mais baixa, {min(top1_resp):.3f}). O score sozinho não decide "
                    f"a recusa; se usar MIN_SCORE, fique em no máximo {limiar:.3f}, só como rede de "
                    "segurança contra perguntas totalmente fora do assunto."
                )
        else:
            m["sugestao"] = f"Sem medições de perguntas sem resposta; limite superior {limiar:.3f}."
    return m


def contaminacao(resultados: list[Resultado]) -> list[str]:
    linhas = []
    for r in resultados:
        if not r.controle or "erro" in r.controle or r.erro:
            continue
        c = r.controle
        linhas.append(
            f"| {r.item['id']}#{r.repeticao} | {r.item['tipo']} | {resumir(r.item['anterior'], 50)} | "
            f"{sim_nao(r.recuperou)} / {sim_nao(c['recuperou'])} | "
            f"{r.posicao_evidencia or '—'} / {c['posicao_evidencia'] or '—'} | "
            f"{fmt(r.score_evidencia)} / {fmt(c['score_evidencia'])} |"
        )
    return linhas


def consistencia(resultados: list[Resultado]) -> list[str]:
    """Com repetições, lista as perguntas cujo resultado mudou entre as rodadas."""
    por_id: dict[str, list[Resultado]] = {}
    for r in resultados:
        por_id.setdefault(r.item["id"], []).append(r)
    variaram = []
    for pid, rs in por_id.items():
        if len({(r.ok, r.encontrou, tuple(r.paginas_citadas)) for r in rs}) > 1:
            variaram.append(pid)
    return variaram


def gerar_relatorio(resultados, metricas, meta, avisos_matriz) -> str:
    L = []
    L.append(f"# Avaliação DocuMind — {meta['modo']} — {meta['data']}")
    L.append("")
    if meta["modo"] == "dry-run":
        L.append("> **DRY-RUN OFFLINE.** Embedder de saco de palavras e cliente falso que sempre "
                 "\"responde\" copiando o 1º trecho. Estes números **não medem a qualidade** do "
                 "DocuMind; só provam que o script roda de ponta a ponta sem chave. "
                 "As recusas das perguntas sem resposta falham de propósito aqui.")
        L.append("")
    L.append("## Configuração")
    L.append("")
    for chave, valor in meta["config"].items():
        L.append(f"- {chave}: {valor}")
    L.append("")
    if avisos_matriz:
        L.append("## Avisos da conferência da matriz")
        L.append("")
        L.extend(f"- {a}" for a in avisos_matriz)
        L.append("")

    L.append("## Métricas agregadas")
    L.append("")
    L.append("| Métrica | Valor |")
    L.append("|---|---|")
    L.append(f"| Execuções (pergunta × repetição) | {metricas['total']} (erros de API: {metricas['erros']}) |")
    L.append(f"| Resultado OK (todos os critérios) | {metricas['ok']} |")
    L.append(f"| Acerto de recuperação (alguma evidência no top-{meta['top_k']}) | {metricas['recuperacao']} |")
    L.append(f"| Recuperação completa (todas as evidências no top-{meta['top_k']}) | {metricas['recuperacao_todas']} |")
    L.append(f"| Citação correta (cita página esperada) | {metricas['citacao']} |")
    L.append(f"| Termos-chave presentes | {metricas['termos']} |")
    L.append(f"| Recusa nas perguntas sem resposta | {metricas['recusa_sem_resposta']} |")
    L.append(f"| Falsa recusa nas respondíveis | {metricas['falsa_recusa']} |")
    L.append(f"| Score top-1, respondíveis | {metricas['top1_resp']} |")
    L.append(f"| Score top-1, sem resposta | {metricas['top1_sem']} |")
    L.append("")
    if "min_score_max" in metricas:
        L.append("### Sugestão de `MIN_SCORE`")
        L.append("")
        L.append(f"- Maior limiar que não recusa nenhuma respondível: **{metricas['min_score_max']:.3f}**.")
        if "margem" in metricas:
            L.append(f"- Margem sobre a sem resposta de maior score: **{metricas['margem']:+.3f}**.")
        L.append(f"- {metricas['sugestao']}")
        L.append("")

    L.append("## Resultado por pergunta")
    L.append("")
    L.append("Legenda: Rec. = evidência no top-k; Cit. = citou página esperada; Recusa ok = "
             "recusou se e só se devia; Pos. = posição da melhor evidência no ranking completo.")
    L.append("")
    L.append("| ID | Tipo | Pergunta | Esperado (páginas) | Resposta observada | Páginas citadas | "
             "Rec. | Cit. | Termos faltando | Recusa ok | Top-1 | Evid. (pos.) | Tempo | Resultado | "
             "Conferência manual |")
    L.append("|" + "---|" * 15)
    for r in resultados:
        item = r.item
        esperado = ", ".join(rotulo(e["arquivo"], e["pagina"]) for e in item["evidencias"]) or "recusa"
        if r.erro:
            observada = f"ERRO: {r.erro}"
        elif r.encontrou:
            observada = r.resposta
        else:
            observada = f"(recusa: {r.motivo_recusa})"
        termos = "—" if not r.respondivel else (
            ", ".join(t.split("|")[0] for t in r.termos_faltando) or "nenhum"
        )
        evid = "—" if r.score_evidencia is None else f"{r.score_evidencia:.3f} ({r.posicao_evidencia})"
        L.append(
            f"| {item['id']}#{r.repeticao} | {item['tipo']} | {resumir(item['pergunta'], 70)} | "
            f"{esperado} | {resumir(observada)} | {', '.join(r.paginas_citadas) or '—'} | "
            f"{sim_nao(r.recuperou)} | {sim_nao(r.citou_certo)} | {resumir(termos, 60)} | "
            f"{sim_nao(r.recusa_correta)} | {fmt(r.score_top1)} | {evid} | {r.tempo:.2f}s | "
            f"{'OK' if r.ok else 'FALHA'} |  |"
        )
    L.append("")

    linhas = contaminacao(resultados)
    if linhas:
        L.append("## Efeito da pergunta anterior na busca")
        L.append("")
        L.append("Cada célula mostra **com a anterior / sem a anterior**. A busca real concatena a "
                 "pergunta anterior à atual. No acompanhamento isso deve ajudar; na pergunta "
                 "independente, pode atrapalhar (contaminação).")
        L.append("")
        L.append("| ID | Tipo | Anterior | Rec. | Posição da evidência | Score da evidência |")
        L.append("|---|---|---|---|---|---|")
        L.extend(linhas)
        L.append("")

    if meta["repeticoes"] > 1:
        variaram = consistencia(resultados)
        L.append("## Variação entre repetições")
        L.append("")
        L.append("Perguntas cujo resultado, recusa ou páginas citadas mudaram entre as rodadas: "
                 + (", ".join(variaram) if variaram else "nenhuma") + ".")
        L.append("")

    L.append("## Conferência manual (obrigatória pelo PLANO)")
    L.append("")
    L.append("Para cada linha respondida, abrir o PDF na página citada, conferir se o texto "
             "sustenta a resposta e escrever OK ou FALHA (com o motivo) na última coluna. "
             "As métricas automáticas não substituem esta etapa.")
    L.append("")
    return "\n".join(L)


# --- Programa principal ----------------------------------------------------------------------


def preparar_real(args):
    """Embedder e gerador reais do Ollama local (o mesmo código usado pelo app)."""
    import os

    from dotenv import load_dotenv

    from src import providers
    from src.config import ConfigError, load_settings

    load_dotenv(override=False)
    env = dict(os.environ)
    if args.modelo:
        env["OLLAMA_MODEL"] = args.modelo
    if args.modelo_embedding:
        env["OLLAMA_EMBEDDING_MODEL"] = args.modelo_embedding
    if args.sem_raciocinio:
        env["DOCUMIND_OLLAMA_THINK"] = "false"
    try:
        settings = load_settings(env=env)
        providers.check_local_ready(settings)
        backend = providers.build_backend(settings)
    except (ConfigError, providers.ProviderError) as erro:
        raise SystemExit(f"Erro de configuração: {erro}")
    return settings, backend


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Avalia a matriz de perguntas do DocuMind.")
    parser.add_argument("--real", action="store_true",
                        help="usa os modelos de verdade (Ollama local por padrão); sem isso, dry-run")
    parser.add_argument("--modelo", default=None, help="com --real: modelo de geração (ex.: qwen3:14b)")
    parser.add_argument("--modelo-embedding", default=None, help="com --real: modelo de embedding")
    parser.add_argument("--sem-raciocinio", action="store_true",
                        help="com --real: desliga o raciocínio do Qwen3 (think=false)")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--overlap", type=int, default=150)
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--repeticoes", type=int, default=1, help="rodadas da matriz inteira")
    parser.add_argument("--min-score", type=float, default=answering.MIN_SCORE,
                        help=f"limiar de recusa por score (padrão: MIN_SCORE do projeto, {answering.MIN_SCORE})")
    parser.add_argument("--pausa", type=float, default=None,
                        help="segundos entre perguntas (padrão: 0)")
    parser.add_argument("--matriz", type=Path, default=MATRIZ)
    parser.add_argument("--so", nargs="*", default=None, help="roda só estes IDs (ex.: --so D1 S1)")
    args = parser.parse_args(argv)

    for fluxo in (sys.stdout, sys.stderr):  # console do Windows: acentos sem erro
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    logging.getLogger("pypdf").setLevel(logging.ERROR)

    if (args.modelo or args.modelo_embedding or args.sem_raciocinio) and not args.real:
        parser.error("--modelo, --modelo-embedding e --sem-raciocinio só valem com --real.")
    if args.repeticoes < 1:
        parser.error("--repeticoes deve ser pelo menos 1.")

    dados = carregar_matriz(args.matriz)
    perguntas = dados["perguntas"]
    if args.so:
        perguntas = [p for p in perguntas if p["id"] in set(args.so)]
        if not perguntas:
            parser.error("nenhum ID de --so existe na matriz.")

    # 1) Documentos: loader e chunking reais.
    arquivos = [(Path(c).name, (RAIZ / c).read_bytes()) for c in dados["documentos"]]
    try:
        carga = load_pdfs(arquivos)
    except PdfLoadError as erro:
        raise SystemExit(f"Erro ao carregar as amostras: {erro}")
    for erro in carga.errors:
        print(f"[aviso] {erro}")
    paginas = {(p.source_name, p.page_number): p.text for p in carga.pages}
    trechos = chunk_pages(carga.pages, args.chunk_size, args.overlap)

    avisos_matriz = conferir_matriz(perguntas, paginas)
    for aviso in avisos_matriz:
        print(f"[matriz] {aviso}")

    # 2) Embedder e gerador: reais ou falsos.
    if args.real:
        settings, backend = preparar_real(args)
        interno, gerador = backend.embedder, backend.generator
        modelo, modelo_emb = settings.model, settings.embedding_model
        sufixo = "" if settings.think else "-sem-raciocinio"
        modo = f"real-ollama-{settings.model.replace(':', '')}{sufixo}"
        pausa_padrao = 0.0
        print(f"Modelos: {backend.label} · raciocínio {'ligado' if settings.think else 'desligado'}")
    else:
        print("=" * 78)
        print("DRY-RUN OFFLINE: embedder de saco de palavras + cliente falso (cita o 1º trecho).")
        print("Os números abaixo NÃO medem a qualidade do DocuMind; só provam que o script roda.")
        print("Para a avaliação de verdade: acrescente --real (Ollama local por padrão).")
        print("=" * 78)
        interno, gerador = EmbedderSacoDePalavras(), GeradorFalso()
        modelo, modelo_emb, modo, pausa_padrao = "falso", "saco-de-palavras", "dry-run", 0.0
    pausa = args.pausa if args.pausa is not None else pausa_padrao
    embedder = EmbedderComMemoria(interno)

    print(f"Indexando {len(trechos)} trechos (chunk {args.chunk_size}, overlap {args.overlap})...")
    inicio_indice = time.perf_counter()
    try:
        index = build_index(trechos, embedder)
    except RetrievalError as erro:
        raise SystemExit(f"Erro ao indexar: {erro}")
    tempo_indice = time.perf_counter() - inicio_indice

    # 3) Perguntas.
    resultados: list[Resultado] = []
    total = len(perguntas) * args.repeticoes
    feitos = 0
    for repeticao in range(1, args.repeticoes + 1):
        for item in perguntas:
            if feitos and pausa > 0:
                time.sleep(pausa)  # respeita a cota por minuto da API
            feitos += 1
            r = avaliar_pergunta(item, repeticao, index, embedder, gerador, args)
            resultados.append(r)
            estado = f"ERRO: {r.erro}" if r.erro else ("OK" if r.ok else "FALHA")
            print(f"[{feitos}/{total}] {item['id']}#{repeticao} {item['tipo']}: {estado} "
                  f"(top-1 {fmt(r.score_top1)}, {r.tempo:.2f}s)")

    # 4) Métricas e relatório.
    metricas = calcular_metricas(resultados)
    agora = datetime.now()
    meta = {
        "modo": modo,
        "data": agora.strftime("%d/%m/%Y %H:%M"),
        "top_k": args.top_k,
        "repeticoes": args.repeticoes,
        "config": {
            "Documentos": ", ".join(Path(c).name for c in dados["documentos"]),
            "Trechos": f"{len(trechos)} (chunk_size {args.chunk_size}, overlap {args.overlap})",
            "Tempo de indexação": f"{tempo_indice:.2f}s",
            "top_k": args.top_k,
            "min_score usado": args.min_score,
            "Repetições": args.repeticoes,
            "Pausa entre perguntas": f"{pausa}s",
            "Modelo de geração": modelo,
            "Raciocínio (think)": ("ligado" if settings.think else "desligado") if args.real else "—",
            "Modelo de embedding": modelo_emb,
            "Perguntas": len(perguntas),
        },
    }
    relatorio = gerar_relatorio(resultados, metricas, meta, avisos_matriz)
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    matriz = "" if args.matriz == MATRIZ else f"-{args.matriz.stem}"
    nome = f"{agora:%Y%m%d-%H%M}-{modo}{matriz}-c{args.chunk_size}-o{args.overlap}-k{args.top_k}.md"
    destino = RESULTADOS / nome
    destino.write_text(relatorio, encoding="utf-8")

    print()
    print(f"Recuperação: {metricas['recuperacao']} | Citação: {metricas['citacao']} | "
          f"Termos: {metricas['termos']}")
    print(f"Recusa sem resposta: {metricas['recusa_sem_resposta']} | "
          f"Falsa recusa: {metricas['falsa_recusa']} | OK: {metricas['ok']}")
    if "sugestao" in metricas:
        print(f"MIN_SCORE: {metricas['sugestao']}")
    try:
        print(f"Relatório: {destino.relative_to(RAIZ)}")
    except ValueError:
        print(f"Relatório: {destino}")
    if not args.real:
        print("Lembrete: dry-run offline, sem valor de qualidade.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
