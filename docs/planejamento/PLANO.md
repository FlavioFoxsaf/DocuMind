# DocuMind — plano de execução e referência para desenvolvimento

**Versão:** 1.1 — 27/09/2026  
**Estado:** MVP implementado e rodando só com modelos locais (Ollama, `qwen3:14b`); Gemini removido em 27/09/2026 (T13)  
**Prazo de referência:** 01/10/2026, 23h59 (horário de Brasília), para candidatos classificados  
**Leitura obrigatória para continuar:** este arquivo → [PLANO_MIGRACAO_LOCAL.md](PLANO_MIGRACAO_LOCAL.md) → [STATUS.md](STATUS.md) → código e testes existentes → [guia de desenvolvimento](../README_DESENVOLVIMENTO.md)

**Organização em 27/09/2026:** os planos e o status foram agrupados em `docs/planejamento/`.
Os caminhos de código e os comandos mencionados aqui são relativos à raiz de `DocuMind`.
A pasta para envio é [`../../../DocuMind_Entrega/`](../../../DocuMind_Entrega/).

**Decisão do usuário em 27/09/2026 (T13), que prevalece sobre o restante deste plano:** o Gemini foi **removido**; o DocuMind funciona só com o Ollama local, e a prioridade é **precisão sobre velocidade**. Referências abaixo a Gemini, `google-genai`, chave de API ou modo opcional são históricas. O `STATUS.md` registra a implementação.

**Mudança de escopo aprovada em 27/09/2026 (anterior):** implementar Ollama como provedor local padrão, sem chave Gemini, para embeddings **e** geração; Gemini permanece opcional e nunca é fallback automático. O [plano de migração local](PLANO_MIGRACAO_LOCAL.md) prevalece sobre referências abaixo que tratam Gemini como obrigatório. O `STATUS.md` prevalece para fatos de implementação e testes. Este plano contém também o histórico da arquitetura original.

## 1. Objetivo e definição de pronto

Construir um protótipo local de chatbot documental em que o usuário envia PDFs, faz perguntas em português e recebe respostas sustentadas por trechos identificáveis dos arquivos. A aplicação deve mostrar arquivo, página e evidência, e declarar quando não encontrou base suficiente. O produto será apresentado em um vídeo de **até 2 minutos** e defendido em entrevista técnica.

O resultado esperado é um **mini NotebookLM de escopo controlado**, não a reprodução de todos os recursos do produto original. O projeto deve ser pequeno o bastante para Flávio conseguir explicar cada etapa e cada decisão sem depender da IA que escreveu o código.

**Concluído somente quando:**

1. Uma pessoa consegue instalar Ollama e os modelos locais, iniciar e usar o app sem chave Gemini seguindo o README. O modo Gemini, se mantido, exige chave apenas quando selecionado.
2. O fluxo completo funciona com um PDF textual e também com mais de um PDF: upload → extração → indexação → pergunta → busca → resposta com fonte.
3. Uma pergunta respondível retorna evidências conferidas manualmente na página citada; uma pergunta sem evidência retorna uma recusa clara.
4. O app informa erros de PDF ilegível/sem texto, Ollama indisponível/modelo ausente e, no modo Gemini opcional, chave ausente/falha da API, sem fingir que produziu uma resposta.
5. Há testes locais pertinentes, uma matriz de perguntas de demonstração, um vídeo final de até 2 minutos e um roteiro de defesa técnica.
6. Flávio consegue explicar e reproduzir o fluxo sem ler o código linha por linha.

## 2. Fonte externa e restrições do edital

Fonte primária local: [`_EDITAL_.pdf`](../../../_EDITAL_.pdf), especialmente itens 3.4.2.7–3.4.2.9, 3.4.3.5, cronograma na página 8 e Anexos I e III. O edital pede **projeto de implementação baseado em IA acompanhado de vídeo explicativo de no máximo 2 minutos**, com envio em **01/10/2026** para classificados na análise curricular. As entrevistas estão previstas de 02/10 a 08/10/2026 e podem tratar de aspectos técnicos, metodológicos e práticos do projeto. O Anexo III dá 15 pontos ao domínio técnico, 10 à desenvoltura, 10 à motivação, 15 à aderência e até 50 à análise curricular.

O edital local não detalha formato do código, repositório, tamanho do vídeo nem campos do formulário de envio. Antes da submissão, conferir o formulário e eventuais comunicados/retificações na [página oficial de editais](https://universidadesenaicimatec.edu.br/editais-e-documentos/). Não deixar essa checagem para os minutos finais.

**Complemento do formulário, transcrito pelo usuário em 27/09/2026:** projeto completo
em uma única pasta compactada (.zip, .7z ou .rar), até 100 MB, com possibilidade de
descompactar e rodar e orientações em `Readme.txt` se necessárias. Vídeo separado de
até 2 minutos e 100 MB, em .mp4 ou .avi, com imagem e voz do candidato, sem uso de IA,
explicação técnica e código de inscrição no edital 032/2026 na apresentação.
A fala final deve ser própria do candidato; o guia de preparação não certifica se
a vedação de IA também abrange auxílio na preparação. Regras adicionais da organização
prevalecem. Detalhes de gravação e checklist em
[roteiro_video.md](<../../../video explicativo/roteiro_video.md>).

## 3. Escopo do MVP

### Obrigatório

- Interface local em Streamlit com upload de 1 a 3 PDFs textuais, processamento explícito, lista de arquivos ativos e chat.
- Limites práticos visíveis: até 10 MB por arquivo e até 100 páginas no conjunto; limites podem ser ajustados após medir desempenho, com registro no STATUS.
- Extração com `pypdf`, preservando nome do arquivo e número da página em base 1. Detectar PDFs sem texto extraível e não indexá-los silenciosamente.
- Normalização leve e divisão por página em trechos com sobreposição. Nenhum trecho deve atravessar páginas, para manter citações corretas.
- Embeddings dos trechos e da pergunta, busca por similaridade de cosseno em memória e seleção de poucos trechos relevantes.
- Geração com Gemini usando **somente** a pergunta, os trechos recuperados e o mínimo de histórico necessário. Sem ferramenta de busca web. Mostrar citações verificáveis e trechos usados.
- Recusa quando não houver evidência adequada. Troca ou remoção de PDFs invalida índice e histórico, evitando mistura entre conjuntos de documentos.
- Mensagens claras de progresso, erro e estado. A chave de API nunca deve aparecer na interface, em logs ou em arquivos versionados.
- README atualizado para refletir o que existe de fato, com instruções reproduzíveis e limitações.

### Depois do MVP, somente se houver tempo

- Melhor tratamento de perguntas de acompanhamento com reescrita da consulta.
- Persistência de índices, OCR para PDFs digitalizados, suporte a outros formatos, autenticação, deploy, FAISS ou banco vetorial, streaming de resposta e visualizador de PDF integrado.

Não acrescentar esses recursos antes de cumprir e verificar o obrigatório. O README inicial menciona FAISS, outras LLMs e “sem alucinação” como intenção; **não são fatos implementados nem promessa de garantia**.

## 4. Arquitetura proposta

```text
PDF(s) enviados
  → validação de tamanho/tipo e extração por página (pypdf)
  → normalização e divisão em trechos com metadados
  → embeddings de documento (Gemini)
  → matriz de vetores da sessão (NumPy)
pergunta + contexto curto da conversa
  → embedding de consulta (mesmo modelo)
  → similaridade de cosseno e top-k
  → verificação de relevância / possibilidade de recusa
  → prompt restrito com trechos identificados
  → resposta do Gemini + validação de IDs citados
  → chat com arquivo, página e trecho de apoio
```

**Stack preferencial:** Python 3.11, Streamlit, `pypdf`, `google-genai`, NumPy e `python-dotenv`. Usar o SDK atual `google-genai`; os nomes exatos dos modelos de geração e embedding ficam configuráveis por variáveis de ambiente e devem ser confirmados na conta disponível durante a implementação. Usar `RETRIEVAL_DOCUMENT` para trechos e `RETRIEVAL_QUERY` para perguntas, quando suportado pelo modelo escolhido. Para poucas dezenas/centenas de trechos, NumPy basta; FAISS introduziria instalação e abstração sem benefício demonstrado para este protótipo.

**Modelo de dados mínimo:** `PageText(source_name, page_number, text)`, `Chunk(chunk_id, source_name, page_number, text)` e `RetrievedChunk(chunk, score)`. Os IDs devem ser estáveis dentro da indexação e únicos entre arquivos. Cada resposta deve citar apenas IDs presentes no contexto fornecido naquele turno. Validar os IDs sintaticamente; isso não prova que o conteúdo da resposta esteja correto, por isso a avaliação manual continua obrigatória.

**Parâmetros iniciais para medir, não “números mágicos”:** trechos de aproximadamente 800–1.200 caracteres, sobreposição de 100–200 caracteres, `top_k=4`. Ajustar somente após rodar a matriz de avaliação e registrar motivo e efeito em `STATUS.md`. Uma nota de similaridade baixa pode ajudar a recusar, mas qualquer limiar precisa ser calibrado em perguntas reais; a ausência de palavra-chave, isoladamente, não prova ausência de resposta.

**Conversa:** guardar histórico apenas na sessão. Em cada nova pergunta, refazer a recuperação documental; nunca usar uma resposta anterior como evidência. Para uma pergunta dependente da anterior, considerar a última pergunta do usuário ao montar a consulta, testar o resultado e documentar a limitação. Não enviar todo o histórico ao modelo por padrão.

**Privacidade:** o texto dos trechos enviados à API sai da máquina do usuário. A demonstração deve usar PDF público, próprio ou autorizado. Não salvar PDFs, trechos, embeddings ou perguntas no disco no MVP; não registrar conteúdo sensível em logs. O estado do Streamlit é temporário e se perde ao reiniciar/recarregar a sessão.

**Limitações declaradas:** PDFs digitalizados sem camada de texto exigem OCR; tabelas e layouts complexos podem ser extraídos incorretamente; recuperação e geração podem errar. “Responder apenas com documentos” é uma política do sistema com verificações, não garantia absoluta contra conhecimento prévio, vieses ou alucinações. O app não substitui interpretação jurídica de uma convenção de condomínio.

**Referências técnicas oficiais para conferir ao implementar:** [upload](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader), [chat](https://docs.streamlit.io/develop/tutorials/chat-and-llm-apps/build-conversational-apps), [estado da sessão](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state), [SDK Gemini](https://ai.google.dev/gemini-api/docs/get-started), [embeddings](https://ai.google.dev/gemini-api/docs/embeddings), [extração com pypdf](https://pypdf.readthedocs.io/en/latest/user/extract-text.html).

## 5. Estrutura alvo e divisão de trabalho

```text
DocuMind/
├── README.md                # índice dos documentos e referências de preparação/entrega
├── .env.example             # nomes das variáveis, sem segredo
├── .gitignore               # .env, .venv, caches e arquivos privados
├── requirements.txt         # dependências realmente usadas
├── app.py                   # somente interface e estado da sessão
├── src/
│   ├── loader.py            # validação, extração e metadados de páginas
│   ├── chunking.py          # normalização e trechos
│   ├── retrieval.py         # embeddings, matriz e busca
│   └── answering.py         # prompt, geração, recusa e fontes
├── tests/                   # testes locais sem chave real; integração se viável
└── docs/                    # planejamento, contratos, amostras e avaliação
    └── planejamento/        # PLANO.md, STATUS.md e PLANO_MIGRACAO_LOCAL.md
```

Materiais de preparação ficam fora da aplicação: [Entrevista/](../../../Entrevista/README.md)
e [video explicativo/](<../../../video explicativo/README.md>), na pasta mãe.

As áreas `loader/chunking`, `retrieval`, `answering`, `app` e `docs/testes` podem ser trabalhadas por IAs diferentes **após** combinar interfaces e responsáveis. Cada responsável deve ler o plano e o status, declarar os arquivos que assumiu no status e não editar o mesmo arquivo simultaneamente com outra IA. Integração, execução e atualização final do status devem ter um único responsável por vez. Nenhuma tarefa é considerada pronta apenas porque o código foi escrito.

## 6. Critérios de aceite e avaliação

### Verificação automatizada

- Extração mantém página correta, inclusive após normalização e chunking; ignora páginas vazias com aviso.
- Troca do conjunto de arquivos recria o índice e limpa respostas antigas.
- Busca retorna trechos ordenados e nunca cita arquivo/página inexistente; testar com embeddings simulados para não depender da API.
- Validação rejeita IDs de fonte inventados pela resposta. Falhas de API e chave ausente produzem erro controlado.
- Executar os testes e registrar comando, resultado e data no `STATUS.md`. Testes de API real são separados e só rodam com chave configurada.

### Verificação manual do fluxo

Preparar um PDF público/autorizado com fatos fáceis de conferir e uma matriz com pelo menos 10 perguntas: 5 diretas, 2 que exigem combinar trechos, 1 de acompanhamento e 2 cuja resposta não conste do documento. Para cada pergunta registrar: resposta esperada, evidência e página, resposta observada, páginas exibidas e resultado. O MVP só passa se as respostas apresentadas na demonstração tiverem suporte nas páginas citadas, se as duas perguntas sem base forem recusadas e se qualquer falha observada estiver documentada. Testar também PDF sem texto e chave ausente. Evitar perguntas decoradas como única avaliação: repetir com ao menos uma paráfrase.

**Métrica simples para explicar na entrevista:** acerto de recuperação (`evidência esperada aparece no top-k?`), taxa de citação correta e taxa de recusa em perguntas sem resposta. Não chamar o sistema de “sem alucinação” por ter passado em poucos exemplos.

## 7. Cronograma de entrega

| Data | Marco verificável | Reserva para aprendizado |
|---|---|---|
| 27/09 | Plano e status prontos; ambiente, PDF de demonstração, extração, trechos e primeira busca. | Explicar o problema, página, chunk, overlap, embedding e cosseno. |
| 28/09 | Resposta citada e recusa funcionando; primeiro fluxo ponta a ponta. | Explicar prompt, contexto, conhecimento prévio e limites. |
| 29/09 | Interface, múltiplos PDFs, erros, README e matriz de avaliação. | Demonstrar e justificar cada módulo do código. |
| 30/09 | Testes finais, roteiro e gravação do vídeo, ensaio de perguntas. | Simular entrevista técnica e corrigir pontos fracos. |
| 01/10 | Checagem de formato/retificações e submissão com antecedência. | Revisão leve; não iniciar recurso novo. |

O vídeo tem meta de **1min50s**, com 10 s de margem: identificação com código e problema
(12 s), fluxo RAG durante o upload (30 s), resposta citada (40 s), pergunta sem base
e limites (20 s), fechamento (8 s). Câmera e voz próprias do candidato; explicação com
suas palavras. Usar o app real e conferir as evidências mostradas. O checklist atual
está em [roteiro_video.md](<../../../video explicativo/roteiro_video.md>).

## 8. Fase posterior: domínio técnico de ponta a ponta

**Atualização de 28/09:** o usuário pediu treinamento antes da gravação. A preparação
até 30/09 segue [treinamento_ponta_a_ponta.md](../../../Entrevista/treinamento_ponta_a_ponta.md):
explicar com palavras próprias, localizar no código e prever comportamento/falhas,
sem modificar a entrega ou repetir a suíte. O estudo é acompanhado por perguntas
uma a uma, com tentativa do aluno antes da correção. Inscrição para o vídeo: **16**.
As alterações de código propostas abaixo ficam para aprofundamento posterior.

Após a entrega, conduzir sessões em que Flávio primeiro explica e demonstra, e a IA corrige lacunas com exemplos do código. Percorrer, nesta ordem: configuração e execução; extração de PDF; chunking; embeddings e similaridade; recuperação e métricas; prompt e geração; citações e recusa; estado do Streamlit; privacidade e custos; testes e depuração; limitações e possíveis evoluções. Em cada etapa, exigir três evidências: explicação com suas palavras, localização do trecho de código e uma alteração pequena feita com entendimento.

Banco inicial de perguntas para a entrevista: por que RAG em vez de enviar o PDF inteiro? Por que dividir por página? Como escolhe `top_k`? O que o escore mede? O que acontece com PDF digitalizado? Como sabe que a citação está certa? O que impede respostas fora do documento? O que acontece se a API falhar? Que dados saem da máquina? Como mediu qualidade? O que faria para escalar? Por que não usar FAISS agora?

## 9. Protocolo de passagem de bastão para qualquer IA

1. Ler este plano, `PLANO_MIGRACAO_LOCAL.md` e `STATUS.md` integralmente; depois inspecionar somente os arquivos necessários à próxima tarefa. O **status prevalece para fatos atuais**; o plano de migração prevalece sobre escolhas antigas de provedor. O README descreve o app atual e deve ser atualizado após a implementação local.
2. Conferir data, prazo e resultados existentes. Não declarar recurso pronto sem código executado ou evidência registrada. Não presumir que uma chave de API está disponível.
3. Escolher a primeira tarefa não concluída cujas dependências estejam satisfeitas; registrar responsável e arquivos antes de trabalho paralelo. Se a prioridade mudar, registrar decisão e motivo.
4. Implementar um incremento executável, verificar o risco correspondente e atualizar `STATUS.md` no mesmo turno com arquivos alterados, comandos/resultados, decisões, bloqueios e **próxima ação única e concreta**.
5. Se código e plano divergirem, corrigir o código ou propor a mudança de escopo no status; manter README e status coerentes. Nunca escrever segredos ou PDFs privados no repositório.
6. Ao parar, deixar o projeto reproduzível para outra IA: estado real, último teste e exatamente de onde continuar. Para relatório ao usuário, dizer claramente o que funciona, o que falta e o que foi verificado.
