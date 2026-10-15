# DocuMind

> Guia técnico do ambiente de desenvolvimento. Execute os comandos a partir da pasta
> `DocuMind`, que contém `app.py`, e não desta pasta `docs`.
> A versão preparada para envio está em [`../../DocuMind_Entrega/`](../../DocuMind_Entrega/),
> com um [Readme.txt próprio para o avaliador](../../DocuMind_Entrega/Readme.txt).

Um mini NotebookLM de escopo controlado: você envia PDFs, faz perguntas em português e
recebe respostas baseadas só nos documentos, com a fonte (arquivo e página) e o trecho
usado. Quando não encontra base suficiente, o app recusa a resposta.

> Protótipo em Python + Streamlit que roda **inteiro nesta máquina com o Ollama**: os
> embeddings e as respostas são gerados localmente, sem chave de API, sem cota e sem enviar
> os documentos para a internet. A configuração prioriza **precisão sobre velocidade**
> (`qwen3:14b` com raciocínio). Testado de ponta a ponta com modelos reais em 27/09/2026
> (veja [Estado atual](#estado-atual)).

## Como funciona

```text
PDFs (1 a 3)
  │ 1. validação e extração de texto por página (pypdf, página em base 1)
  ▼
páginas ── 2. normalização e trechos de até 1.000 caracteres, sobreposição de até 150,
  │           sem atravessar páginas (ID S<arquivo>-P<página>-C<trecho>)
  ▼
trechos ── 3. embeddings locais (qwen3-embedding:0.6b) → matriz NumPy normalizada em L2
  │
pergunta ── 4. embedding da pergunta (mesmo modelo, com instrução de busca) → cosseno → top-4
  │
  ├─ 5. melhor score abaixo de MIN_SCORE → recusa, sem chamar o modelo (hoje desligado)
  ▼
  6. prompt restrito (regras + trechos delimitados) → qwen3:14b com raciocínio e JSON Schema
  │     {"status": "answered" | "not_found", "answer": ..., "citations": [IDs]}
  ▼
  7. validação: os IDs citados precisam estar entre os trechos deste turno
  ▼
  8. resposta com "arquivo — p. N" e trechos, ou recusa explícita
```

- `src/loader.py`: validação dos limites e extração por página.
- `src/chunking.py`: normalização (NFC, controles e espaços) e trechos com sobreposição.
- `src/config.py`: modelos, endereço (só local), timeout e raciocínio.
- `src/ollama_client.py`: cliente HTTP mínimo da API local do Ollama.
- `src/providers.py`: monta o embedder e o gerador e confere se o Ollama e os modelos estão prontos.
- `src/retrieval.py`: embeddings em lotes, índice em memória e busca por cosseno.
- `src/answering.py`: prompt, geração, validação das citações e recusa.
- `app.py`: só a interface e o estado da sessão.

Os contratos de cada módulo estão em [`docs/contratos/`](contratos/); o dos modelos
locais está em [`providers.md`](contratos/providers.md).

Numa pergunta de acompanhamento ("E às segundas?"), a busca usa a pergunta anterior junto
com a atual. O prompt também recebe a pergunta anterior, marcada como "não é fonte".
Respostas anteriores nunca são usadas como evidência.

## Instalação (Windows)

Requisitos: Python 3.11 (fixado em `.python-version`), o [Ollama para Windows](https://ollama.com/download/windows),
cerca de **10 GB livres** em disco para os modelos e, para a configuração padrão, uma GPU
com **cerca de 13 GB de memória livre** (veja [Memória](#memória-e-desempenho)). Os comandos
rodam no PowerShell, a partir da pasta `DocuMind`. A internet só é necessária para instalar
e baixar os modelos; depois disso o app funciona sem ela.

### 1. Ollama e modelos (uma vez)

```powershell
winget install --id Ollama.Ollama -e --source winget   # ou o instalador do site
# Abra o app "Ollama" (ele fica na bandeja e serve em http://127.0.0.1:11434)
# ou, num terminal separado: ollama serve

ollama pull qwen3:14b                # geração (padrão), ~9,3 GB
ollama pull qwen3-embedding:0.6b     # embeddings, ~0,6 GB

ollama list                          # os dois modelos devem aparecer
Invoke-RestMethod http://127.0.0.1:11434/api/version   # o serviço deve responder
```

O instalador do `winget` coloca o executável em `%LOCALAPPDATA%\Programs\Ollama`. Se o
comando `ollama` não for encontrado logo após instalar, abra um novo terminal.

### 2. Ambiente Python

Com uv (como o ambiente foi criado):

```powershell
uv venv --python 3.11 .venv
uv pip install --python .venv -r requirements.txt       # só para usar o app
uv pip install --python .venv -r requirements-dev.txt   # app + pytest + fpdf2 (testes e amostras)
```

O `.venv` criado pelo uv não tem `pip`. Por isso, instale sempre com `uv pip ... --python .venv`.
Sem uv:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt       # ou requirements-dev.txt
```

### 3. Configuração (opcional)

Sem `.env`, valem os padrões abaixo. Para mudar algo, copie o modelo e edite:

```powershell
Copy-Item .env.example .env
```

| Variável | Padrão | Para quê |
|---|---|---|
| `OLLAMA_MODEL` | `qwen3:14b` | modelo de geração; `qwen3:8b` é mais rápido e leve, e um pouco menos preciso |
| `OLLAMA_EMBEDDING_MODEL` | `qwen3-embedding:0.6b` | modelo de embedding (trechos e perguntas) |
| `DOCUMIND_OLLAMA_URL` | `http://127.0.0.1:11434` | só aceita endereços desta máquina |
| `DOCUMIND_OLLAMA_TIMEOUT` | `180` | segundos; a primeira resposta inclui carregar o modelo |
| `DOCUMIND_OLLAMA_THINK` | `true` | raciocínio do Qwen3 antes de responder (ver decisões) |

Uma variável já definida no sistema vale mais que o `.env`. O `.env` está no `.gitignore`.
Variáveis antigas do Gemini (`GEMINI_*`, `DOCUMIND_PROVIDER`), se sobrarem no seu `.env`,
são ignoradas e podem ser apagadas.

### 4. Execução

```powershell
.venv\Scripts\streamlit run app.py
```

O app abre em `http://localhost:8501` e escuta só nesta máquina (`address = "localhost"`
em `.streamlit/config.toml`). A barra lateral mostra os modelos ativos. Se o Ollama estiver
desligado ou faltar um modelo, o app mostra a instrução de correção (abrir o Ollama ou
rodar `ollama pull <modelo>`) e não carrega o chat; ele não baixa modelos sozinho.
**Depois de mudar o `.env`, reinicie o app** (Ctrl+C e o comando acima).

### Memória e desempenho

Medido numa RTX 5080 de 16 GB: com os dois modelos carregados, o `ollama ps` mostrou
10 GB (`qwen3:14b`) + 2,4 GB (embeddings), 100% na GPU, e a placa ficou com 15,5 de 16,3 GB
ocupados, contando os outros programas abertos. Se a GPU tiver menos memória livre, o
Ollama passa parte do modelo para a CPU e as respostas ficam bem mais lentas (não medido).
Nesse caso, use `OLLAMA_MODEL=qwen3:8b` (5,6 GB na GPU), que acertou 45/48 na matriz difícil
contra 48/48 do 14b.

A **primeira pergunta** depois de ligar o Ollama leva de 20 a 30 s, porque o modelo é
carregado na GPU. Depois disso, na avaliação, o 14b levou mediana de 3,6 s por resposta
(o 8b, 2,3 s).

## Uso

1. Na barra lateral, envie de 1 a 3 PDFs com texto selecionável.
2. Clique em **Processar documentos**. O app extrai as páginas, gera os trechos e os
   embeddings e lista os documentos ativos (páginas com texto e número de trechos).
3. Faça a pergunta no chat.
4. Confira a resposta: a seção **Fontes** lista `arquivo — p. N`. Cada trecho citado abre
   num expander com ID e score, e **Trechos consultados** mostra tudo o que foi enviado ao
   modelo. Se o modelo citar um ID inexistente, o app descarta a citação e avisa.
5. Se trocar ou remover arquivos, ou mudar o modelo de embedding, o índice e a conversa são
   descartados: clique em Processar de novo. O botão **Limpar conversa** apaga só o histórico.

### Amostras de demonstração

Em [`docs/amostras/`](amostras/) há quatro PDFs **fictícios**, escritos para este
projeto: um regulamento de condomínio (6 páginas), uma ata de assembleia (2 páginas), um
aviso com uma página em branco e um PDF sem camada de texto (para testar a detecção).
O gabarito com a página de cada fato está em [`FATOS.md`](amostras/FATOS.md).
Os PDFs são gerados de forma determinística (requer `requirements-dev.txt`):

```powershell
.venv\Scripts\python docs\amostras\gerar_amostras.py
```

Exemplos de pergunta: "Qual a taxa da churrasqueira?" (regulamento, p. 3),
"Qual é o valor da multa na primeira reincidência depois de maio de 2026?" (regulamento
p. 6 + ata p. 1: R$ 680,00) e "Qual é o CNPJ do condomínio?" (não consta; a resposta
esperada é a recusa).

## Testes

```powershell
.venv\Scripts\python -m pytest -q -W error
```

Resultado em 27/09/2026, com o Ollama e os modelos instalados: **434 passed** em cerca de
25 s. Isso inclui:

- testes unitários com clientes falsos (sem rede): loader, chunking, configuração, cliente
  do Ollama, embeddings, busca, prompt, parser, citações e recusa;
- a interface com o `AppTest` do Streamlit (`tests/test_app.py` e `tests/test_app_local.py`),
  com upload real das amostras;
- `tests/test_integration_ollama.py` (5 testes reais): embeddings, resposta com a página
  certa, recusa, o fluxo inteiro com **toda conexão fora de 127.0.0.1 bloqueada** e o
  `app.py` real em processo limpo.

Sem o Ollama (ou sem os modelos), os 5 testes reais são pulados e o resto roda normalmente.

### Avaliação

```powershell
.venv\Scripts\python docs\avaliacao\avaliar.py --real --repeticoes 3
.venv\Scripts\python docs\avaliacao\avaliar.py --real --repeticoes 3 --matriz docs\avaliacao\matriz_dificil.json
.venv\Scripts\python docs\avaliacao\injecao.py --repeticoes 3
```

Veja [`docs/avaliacao/README.md`](avaliacao/README.md) e o índice dos relatórios em
[`docs/avaliacao/resultados/INDICE.md`](avaliacao/resultados/INDICE.md).

## Decisões técnicas

| Decisão | Por quê |
|---|---|
| Só modelos locais (Ollama) | Privacidade (nada sai da máquina), sem chave, sem custo por uso e sem cota. O projeto começou com a API Gemini, que bateu no limite gratuito (HTTP 429) durante a avaliação; o Gemini foi removido em 27/09/2026. |
| `qwen3:14b` como padrão, e não o 8b | Na matriz difícil, o 14b fez 48/48 e o 8b, 45/48: o 8b errou 3 de 3 vezes a conta "3 × R$ 680,00 = R$ 2.040,00". O 14b é cerca de 1,5 vez mais lento; a prioridade é a precisão. |
| Raciocínio (think) ligado | Sem raciocínio, o 8b caiu para 35/48 na matriz difícil (errou armadilhas de horário, contas e negações). O raciocínio é descartado e não aparece na tela. |
| Amostragem recomendada do Qwen3, `seed` fixa e teto de tokens | Com raciocínio e `temperature 0`, o modelo entrou num laço até o timeout de 180 s num teste. A recomendação oficial (`temperature 0.6`, `top_p 0.95`, `top_k 20`) evita isso; a `seed` 42 deixa a resposta repetível, e o `num_predict` transforma um laço em erro controlado. |
| Instrução na frente da pergunta no embedding | É o uso recomendado do Qwen3-Embedding para busca (perguntas e trechos têm papéis diferentes). |
| Índice guarda o modelo de embedding (`embedder_id`) | Vetores de modelos diferentes não se comparam, mesmo com a mesma dimensão. A busca com outro modelo é recusada e o app reindexa. |
| NumPy em memória em vez de FAISS | Com dezenas ou centenas de trechos, uma multiplicação de matriz basta. FAISS acrescentaria instalação e abstração sem ganho medido. |
| Trechos dentro de uma única página | Todo trecho tem exatamente um arquivo e uma página, então a citação nunca fica ambígua. |
| JSON Schema na geração e validação dos IDs | A saída tem formato fixo (status, resposta, citações). Só são aceitos IDs presentes no contexto do turno, e uma resposta sem nenhuma citação válida é descartada. Isso prova que a fonte existe, não que a resposta esteja certa. |
| Recusa explícita | O app recusa quando o modelo devolve `not_found`, quando a resposta vem vazia, quando nenhuma citação é válida ou quando o melhor score fica abaixo de `MIN_SCORE`. |
| Neutralização de delimitadores | Cada trecho vai entre `<trecho ...>` e `</trecho>`. Se o PDF contiver essas marcas, o `<` vira `&lt;`. No teste real de injeção (9/9), o modelo nunca adotou a ordem escondida no PDF, mas chegou a mencionar o valor falso como "informação contraditória", citando a fonte: a defesa não apaga o texto malicioso, por isso a fonte aparece na tela. |

## Limites e privacidade

- **Tudo local:** PDFs, trechos, embeddings e perguntas são processados pelo Ollama nesta
  máquina. A URL do Ollama só aceita `localhost`/`127.0.0.1`/`::1`, e um teste roda o fluxo
  inteiro com toda conexão externa bloqueada. Não selecione modelos "cloud" do Ollama.
- **Hardware:** a configuração padrão usa quase toda uma GPU de 16 GB. Em máquinas mais
  fracas, use o `qwen3:8b`; sem GPU, tudo fica bem mais lento (não medido). Outra máquina
  precisa instalar o Ollama e baixar os modelos (~10 GB).
- **Sem OCR:** PDFs digitalizados, sem camada de texto, são detectados e recusados com uma
  mensagem, sem derrubar os outros arquivos. Páginas em branco são ignoradas com aviso.
  Tabelas e layouts complexos podem ser extraídos de forma incorreta.
- **Limites:** até 3 arquivos, 10 MB cada e 100 páginas no total. Nomes duplicados são
  recusados.
- **Nada é salvo em disco:** PDFs, trechos, embeddings e conversa ficam só na sessão do
  Streamlit e se perdem ao recarregar ou reiniciar.
- **Sem garantia contra alucinação:** "responder só com os documentos" é uma política
  aplicada com prompt e verificações, e não uma garantia. O modelo pode errar; confira
  sempre a página citada.
- **`MIN_SCORE` desligado (`0.0`):** nos testes, os scores **não separam** perguntas com e
  sem resposta, então as recusas vêm do modelo (`not_found`) e da validação das citações.
- **Não substitui interpretação jurídica** de regulamentos, convenções ou contratos.
- **Avaliação limitada:** o corpus de demonstração é fictício e pequeno (9 a 15 trechos),
  então acertar a busca com top-4 é fácil e não prova qualidade em documentos maiores.

## Estado atual

Verificado em 27/09/2026 (Windows 11, RTX 5080 16 GB, Ollama 0.34.4, `qwen3:14b`):

- **App real:** sem chave, com o `.env` presente, o app subiu, indexou regulamento + ata,
  respondeu à pergunta combinada com R$ 680,00 citando regulamento p. 6 e ata p. 1 e recusou
  a pergunta do CNPJ.
- **Avaliação real:** matriz principal **48/48** (1000/150 × 3) e **16/16** (500/100); matriz
  difícil **48/48** (× 3); injeção pelo PDF **9/9**. As respostas foram conferidas
  manualmente com o `FATOS.md`.
- **Sem internet:** o fluxo inteiro funciona com todas as conexões fora de 127.0.0.1 bloqueadas.
- **Erros:** Ollama desligado, modelo ausente, timeout, resposta cortada e resposta inválida
  viram mensagens com instrução, sem traceback.

Pendente: gravar o vídeo, ensaiar a defesa, medir em outra máquina ou sem GPU e avaliar com
documentos maiores e reais. Os detalhes e o próximo passo estão em [`STATUS.md`](planejamento/STATUS.md);
o escopo em [`PLANO.md`](planejamento/PLANO.md).

## Estrutura

```text
DocuMind/
├── app.py                    # interface Streamlit e estado da sessão
├── src/
│   ├── loader.py             # validação e extração por página
│   ├── chunking.py           # normalização e trechos
│   ├── config.py             # modelos, URL local, timeout e raciocínio (.env opcional)
│   ├── ollama_client.py      # cliente HTTP da API local do Ollama
│   ├── providers.py          # embedder + gerador e checagem do Ollama
│   ├── retrieval.py          # embeddings locais e busca por cosseno (NumPy)
│   └── answering.py          # prompt, JSON Schema, geração, citações e recusa
├── tests/                    # unitários, AppTest e integração real com o Ollama
├── docs/
│   ├── README_DESENVOLVIMENTO.md # este guia técnico
│   ├── planejamento/          # PLANO.md, PLANO_MIGRACAO_LOCAL.md e STATUS.md
│   ├── contratos/            # contrato de cada módulo (providers.md = modelos locais)
│   ├── amostras/             # PDFs fictícios, FATOS.md e gerar_amostras.py
│   └── avaliacao/            # matrizes, avaliar.py, injecao.py e relatórios (INDICE.md)
├── .streamlit/config.toml    # upload até 10 MB; só localhost; detalhes de erro ocultos
├── .env.example              # modelo do .env (opcional, sem segredo)
├── .python-version           # 3.11
├── requirements.txt          # dependências do app
├── requirements-dev.txt      # + pytest e fpdf2
├── pytest.ini
└── README.md                 # índice dos materiais e referência da entrega
```

Preparação externa à pasta de desenvolvimento:
[Entrevista/](../../Entrevista/README.md) reúne treinamento e defesa técnica;
[video explicativo/](<../../video explicativo/README.md>) reúne roteiro, ensaios,
gravações e exportação final. Esses materiais não entram no ZIP do programa.

## Autor

Desenvolvido por **Flávio** como projeto prático em Big Data, Engenharia de Dados e
Inteligência Artificial.
