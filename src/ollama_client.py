"""Cliente HTTP mínimo para a API local do Ollama (http://127.0.0.1:11434).

Só três chamadas: listar modelos instalados (/api/tags), gerar embeddings (/api/embed) e
conversar (/api/chat). Nada é baixado daqui: se faltar um modelo, a mensagem manda o
usuário rodar `ollama pull`. Erros viram OllamaError com texto pronto para a tela; o
conteúdo dos documentos nunca entra nessas mensagens.
"""

from collections.abc import Sequence

import httpx

# Conectar a um serviço local é imediato; se não conectar em 3 s, ele está desligado.
_CONNECT_TIMEOUT = 3.0


class OllamaError(Exception):
    """Mensagem pronta para o usuário (pt-BR)."""


class OllamaClient:
    def __init__(self, base_url: str, timeout: float, transport: httpx.BaseTransport | None = None):
        # transport permite testar com respostas simuladas (httpx.MockTransport), sem rede.
        self._base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout, connect=_CONNECT_TIMEOUT),
            transport=transport,
        )

    def __repr__(self) -> str:
        return f"OllamaClient({self._base_url!r})"

    def close(self) -> None:
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _post(self, path: str, payload: dict, model: str) -> dict:
        try:
            response = self._http.post(path, json=payload)
        except httpx.ConnectError as error:
            raise OllamaError(_not_running(self._base_url)) from error
        except httpx.TimeoutException as error:
            raise OllamaError(
                "O Ollama demorou demais para responder. Na primeira pergunta o modelo é "
                "carregado na memória; tente de novo ou aumente DOCUMIND_OLLAMA_TIMEOUT."
            ) from error
        except httpx.HTTPError as error:
            raise OllamaError(f"Falha de comunicação com o Ollama local ({type(error).__name__}).") from error
        return _json_or_error(response, model)

    def list_models(self) -> set[str]:
        """Nomes dos modelos instalados, como aparecem em `ollama list`."""
        try:
            response = self._http.get("/api/tags", timeout=_CONNECT_TIMEOUT)
        except httpx.HTTPError as error:
            raise OllamaError(_not_running(self._base_url)) from error
        data = _json_or_error(response, model="")
        return {item.get("name", "") for item in data.get("models") or []}

    def embed(self, model: str, texts: Sequence[str]) -> list:
        """Um vetor por texto, na mesma ordem (resposta de /api/embed)."""
        data = self._post("/api/embed", {"model": model, "input": list(texts)}, model)
        return data.get("embeddings")

    def chat(
        self, model: str, prompt: str, schema: dict, options: dict | None = None, think: bool = False
    ) -> dict:
        """Uma resposta não transmitida em partes, restrita ao JSON Schema dado.

        Com think=True, o Qwen3 raciocina antes de responder; o raciocínio vem separado em
        message.thinking e a resposta final (o JSON) em message.content. Com think=False, só
        a resposta final é gerada.
        """
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": schema,
            "think": think,
            "options": options or {},
        }
        return self._post("/api/chat", payload, model)


def _not_running(base_url: str) -> str:
    return (
        f"Não foi possível conectar ao Ollama em {base_url}. Verifique se ele está "
        "instalado e em execução (abra o app Ollama ou rode `ollama serve`)."
    )


def _json_or_error(response: httpx.Response, model: str) -> dict:
    try:
        data = response.json()
    except ValueError:
        if response.status_code < 400:
            _raise("O Ollama devolveu uma resposta em formato inesperado.")
        data = {}
    if response.status_code == 404 and model:
        return _raise(f"O modelo {model} não está instalado no Ollama. Rode: ollama pull {model}")
    if response.status_code >= 400:
        detail = str(data.get("error", "")) if isinstance(data, dict) else ""
        # A mensagem do Ollama é técnica e curta (ex.: falta de memória); não traz o documento.
        return _raise(f"O Ollama recusou a requisição (HTTP {response.status_code}). {detail[:200]}".strip())
    if not isinstance(data, dict):
        return _raise("O Ollama devolveu uma resposta em formato inesperado.")
    return data


def _raise(message: str):
    raise OllamaError(message)


def missing_models(client: OllamaClient, models: Sequence[str]) -> list[str]:
    """Modelos pedidos que não aparecem em /api/tags ("x" casa com "x:latest")."""
    installed = client.list_models()
    names = installed | {name.removesuffix(":latest") for name in installed}
    return [model for model in models if model not in names]
