# DocuMind — migração para modelos locais

> Este plano foi movido para `docs/planejamento/`. Os caminhos de código, contratos e
> comandos continuam relativos à raiz da pasta de desenvolvimento `DocuMind`.

**Criado em:** 27/09/2026  
**Estado:** implementado e verificado com modelos reais em 27/09/2026 (L1–L5). **Atualização T13 (mesmo dia):** a pedido do usuário, o Gemini deixou de ser opcional e foi removido do código, das dependências e dos testes; o modelo padrão passou a `qwen3:14b` (precisão). Os trechos deste plano sobre Gemini opcional são históricos  
**Prioridade:** antes de concluir T07, gravar o vídeo e preparar a defesa  
**Prazo de referência:** 01/10/2026, 23h59 (horário de Brasília)

## Instrução de passagem de bastão para Claude ou outra IA

Leia `PLANO.md`, `STATUS.md`, este arquivo, o código, os contratos em `docs/contratos/` e os testes relacionados. **Implemente a migração**, não apenas a documente. O `STATUS.md` registra o estado real e a próxima ação; este arquivo define o novo escopo. Registre cada incremento e as verificações executadas no `STATUS.md`. Preserve o fluxo comprovado enquanto migra, mas faça o caminho local funcionar **sem `GEMINI_API_KEY`**. Não leia nem imprima o valor de `.env` nos relatórios e não altere a chave existente.

## Objetivo e decisão

O DocuMind deve executar o fluxo PDF → extração → trechos → embeddings → busca → geração → citações usando **modelos instalados no próprio computador**. O modo padrão será `ollama`, com chamadas somente para `http://127.0.0.1:11434` ou `localhost`, sem chave, internet ou cota de geração **depois da instalação e do download inicial dos modelos**. Gemini poderá permanecer como modo **opcional e explícito** (`DOCUMIND_PROVIDER=gemini`), útil para comparar resultados; não deve ser acionado automaticamente se Ollama falhar, pois isso enviaria trechos privados para fora sem escolha do usuário. Não misturar embeddings Gemini e Ollama no mesmo índice.

**Ollama** é o executor/servidor local; **Qwen3** é a família de modelos proposta inicialmente. Não chamar o executor de “modelo Llama”. Candidatos iniciais: `qwen3:8b` para respostas e `qwen3-embedding:0.6b` para embeddings. Confirmar nomes e compatibilidade na versão instalada. Ajustar o candidato se a matriz real demonstrar problema de qualidade ou desempenho; registrar evidência e motivo. A máquina inspecionada tem 32 GB de RAM e RTX 5080 de 16 GB, mas verificar espaço livre, instalação, uso efetivo da GPU e tempos antes de prometer desempenho.

## Resultado obrigatório

1. Instalação documentada de Python, Ollama e dos dois modelos, com comandos Windows/PowerShell e checagem de serviço/modelos presentes. O app deve dar erro claro se o Ollama estiver desligado ou se faltar um modelo, sem traceback ou travamento prolongado. Não fazer download silencioso ao abrir o app.
2. `DOCUMIND_PROVIDER=ollama` por padrão, inclusive sem arquivo `.env`. O modo local não exige `GEMINI_API_KEY`, não cria cliente Gemini e não envia PDFs, trechos, embeddings ou perguntas para serviços externos. `DOCUMIND_PROVIDER=gemini` exige chave e mantém mensagens de erro existentes.
3. Embeddings locais **para os trechos e para cada pergunta**, sempre com o mesmo modelo de embedding. Continuar usando a matriz NumPy, cosseno, IDs, arquivo e página. Conferir forma dos vetores, quantidade, valores finitos e erros de conexão, como já é feito para Gemini.
4. Geração local com o mesmo prompt restrito e o mesmo contrato de resposta (`status`, `answer`, `citations`). Usar saída estruturada JSON Schema do Ollama quando suportada e manter `parse_model_reply`, validação de IDs, recusa e tratamento de resposta vazia. Testar se o modelo devolve o JSON em `message.content`, inclusive com eventual modo de raciocínio desativado para a resposta final. Não afirmar que citações tornam a resposta factual por si só.
5. A interface deve mostrar qual provedor/modelo está ativo e uma nota de privacidade correta para esse modo. Não exibir “falta chave Gemini” no modo local. Se houver troca de provedor, modelo de embedding ou conjunto de PDFs na mesma sessão, invalidar índice e conversa para não combinar vetores de espaços diferentes.
6. README, `.env.example`, contratos, matriz de avaliação, roteiro de vídeo e defesa técnica atualizados **após a implementação** para descrever apenas o comportamento verificado. Distinguir claramente modo local de Gemini opcional. Não apresentar o modo local como concluído antes de teste real.

## Sequência técnica sugerida

| Etapa | Alteração | Verificação para encerrar |
|---|---|---|
| L1 — contrato e configuração | Definir interface pequena para `Embedder` (já existe) e gerador de resposta; acrescentar provedor/modelos locais em `src/config.py`, `.env.example` e contratos. Escolher `ollama` sem chave por padrão e validar provedor desconhecido. | Testes de configuração sem `.env`, modo Gemini com/sem chave e seleção de backend. |
| L2 — busca local | Implementar adaptador de embeddings Ollama, preferencialmente isolado da busca vetorial em `src/retrieval.py` ou módulo próprio. Usar entrada em lote se suportada; usar o mesmo modelo para documentos e perguntas. | Testes com cliente falso: dimensão, contagem, NaN/inf, lote vazio, ordem, timeout, serviço desligado e modelo ausente. |
| L3 — resposta local | Isolar a chamada ao modelo de `src/answering.py` sem duplicar prompt, parser, política de recusa ou validação de citações. Implementar adaptador Ollama com JSON Schema. | Testes com resposta válida, `not_found`, JSON inválido, IDs inventados, resposta vazia, erro de serviço/modelo. |
| L4 — interface e estado | Em `app.py`, montar cliente/embedder/gerador a partir do provedor, sem importar ou construir o cliente Gemini no caminho local; atualizar mensagens e estado. | `AppTest` sem chave, upload, processamento, pergunta, citação, troca de PDF/provedor/modelo e falha local tratada. |
| L5 — execução real e avaliação | Instalar Ollama e baixar modelos no ambiente autorizado; executar fluxo real e matriz de perguntas com PDFs fictícios. Comparar páginas, recusas, latência e falhas com o Gemini, sem usar o score antigo como limiar local. | Relatório versionável sem PDF privado ou segredo; conferência manual das fontes; teste offline depois do download inicial; suíte completa; README e roteiro atualizados. |

Arquivos provavelmente afetados: `src/config.py`, `src/retrieval.py`, `src/answering.py`, `app.py`, `requirements.txt`, `.env.example`, `tests/test_config.py`, `tests/test_retrieval.py`, `tests/test_answering.py`, `tests/test_app.py`, `docs/avaliacao/avaliar.py`, contratos, `README.md`, `STATUS.md`, `docs/roteiro_video.md` e `docs/defesa_tecnica.md`. Um módulo `src/providers.py` ou adaptadores separados é aceitável se mantiver as funções atuais testáveis. Não introduzir FAISS, banco vetorial, OCR ou deploy nesta migração.

## Critérios de aceite executáveis

- Sem `.env` e sem `GEMINI_API_KEY`, com Ollama e modelos já instalados, o app inicia e responde a perguntas sobre pelo menos dois PDFs; a resposta mostra arquivo, página e trecho. Desligar a internet durante uma consulta de demonstração não deve quebrar o caminho local. Verificar também que não houve chamada a `google.genai` nesse caminho.
- Uma pergunta cuja resposta não consta dos PDFs retorna recusa, sem citação inventada. Perguntas diretas, entre PDFs e de acompanhamento devem ser testadas; verificar manualmente a página de cada resposta usada no vídeo.
- Sem Ollama ou sem um dos modelos, há instrução prática de correção e nenhum uso automático de Gemini. Com `DOCUMIND_PROVIDER=gemini` e sem chave, há erro controlado; com chave, o fluxo legado continua testável se houver cota.
- Trocar de modelo de embedding exige reindexar os documentos; teste automático impede usar a matriz antiga com vetores novos. `MIN_SCORE` deve ser recalibrado com embeddings locais; não transferir limiar medido no Gemini.
- Suíte automatizada existente continua passando. A avaliação **real** local roda com os modelos baixados, sem chave; registrar resultado por pergunta, tempos de processamento/resposta e limitações. `dry-run` com cliente falso não conta como teste de qualidade.
- README oferece comandos completos para instalar Ollama, baixar os modelos, iniciar o serviço e rodar Streamlit; explica dependências de memória/disco, tempo inicial e privacidade. Vídeo e defesa técnica refletem o backend efetivamente demonstrado.

## Riscos, limites e ordem de prioridade

O modelo local pode ser mais lento e errar formato, recusa ou citações; a existência de JSON Schema não elimina erros factuais. O primeiro download precisa de internet e espaço livre. Em outra máquina, também será necessário instalar Ollama e baixar modelos. Privacidade local depende de usar efetivamente o endereço local e modelos baixados, sem selecionar Ollama Cloud. Mantenha timeout explícito e mensagem de erro objetiva, mas não force um fallback remoto.

Priorize um **fluxo local ponta a ponta funcionando e demonstrável** antes de otimizar velocidade ou refatorar amplamente. Se a instalação local real ficar bloqueada, conclua e teste o código com clientes falsos, registre exatamente o que falta e mantenha o caminho Gemini comprovado para não comprometer o vídeo. Não marque L5 como concluída por inferência.

Referências oficiais: [API local do Ollama](https://docs.ollama.com/api/introduction), [embeddings](https://docs.ollama.com/capabilities/embeddings), [saída estruturada](https://docs.ollama.com/capabilities/structured-outputs), [instalação Windows](https://ollama.com/download/windows), [qwen3:8b](https://ollama.com/library/qwen3:8b) e [qwen3-embedding:0.6b](https://ollama.com/library/qwen3-embedding:0.6b).
