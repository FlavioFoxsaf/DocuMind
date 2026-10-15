# Avaliação DocuMind — real-ollama-qwen314b — 27/09/2026 19:35

## Configuração

- Documentos: regulamento_condominio.pdf, ata_assembleia_2026.pdf
- Trechos: 9 (chunk_size 1000, overlap 150)
- Tempo de indexação: 0.16s
- top_k: 2
- min_score usado: 0.0
- Repetições: 1
- Pausa entre perguntas: 0.0s
- Modelo de geração: qwen3:14b
- Raciocínio (think): ligado
- Modelo de embedding: qwen3-embedding:0.6b
- Perguntas: 16

## Avisos da conferência da matriz

- H6: termo '7.000|7000|sete mil' não aparece nas páginas esperadas.
- H7: termo '17' não aparece nas páginas esperadas.
- H13: termo '2.040|2040' não aparece nas páginas esperadas.
- H15: termo 'não|nao' não aparece nas páginas esperadas.

## Métricas agregadas

| Métrica | Valor |
|---|---|
| Execuções (pergunta × repetição) | 16 (erros de API: 0) |
| Resultado OK (todos os critérios) | 15/16 (94%) |
| Acerto de recuperação (alguma evidência no top-2) | 12/12 (100%) |
| Recuperação completa (todas as evidências no top-2) | 11/12 (92%) |
| Citação correta (cita página esperada) | 12/12 (100%) |
| Termos-chave presentes | 11/12 (92%) |
| Recusa nas perguntas sem resposta | 4/4 (100%) |
| Falsa recusa nas respondíveis | 0/12 (0%) |
| Score top-1, respondíveis | n=12, mín 0.429, mediana 0.611, máx 0.786 |
| Score top-1, sem resposta | n=4, mín 0.510, mediana 0.649, máx 0.729 |

### Sugestão de `MIN_SCORE`

- Maior limiar que não recusa nenhuma respondível: **0.428**.
- Margem sobre a sem resposta de maior score: **-0.301**.
- Os scores NÃO separam as classes (a sem resposta mais alta, 0.729, passa a respondível mais baixa, 0.429). O score sozinho não decide a recusa; se usar MIN_SCORE, fique em no máximo 0.428, só como rede de segurança contra perguntas totalmente fora do assunto.

## Resultado por pergunta

Legenda: Rec. = evidência no top-k; Cit. = citou página esperada; Recusa ok = recusou se e só se devia; Pos. = posição da melhor evidência no ranking completo.

| ID | Tipo | Pergunta | Esperado (páginas) | Resposta observada | Páginas citadas | Rec. | Cit. | Termos faltando | Recusa ok | Top-1 | Evid. (pos.) | Tempo | Resultado | Conferência manual |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1#1 | armadilha | Posso usar a churrasqueira até meia-noite numa sexta-feira? | regulamento_condominio.pdf p.3 | Não, a churrasqueira deve ser usada até 22h, conforme o Art. 10 do regulamento. O uso até meia-noite não está autorizado nos documentos. | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.594 | 0.594 (1) | 3.94s | OK |  |
| H2#1 | armadilha | Uma criança de 11 anos pode usar a piscina sozinha? | regulamento_condominio.pdf p.3 | Não, crianças menores de 12 anos só podem usar a piscina acompanhadas de um adulto responsável, conforme determinado no Art. 8º. | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.599 | 0.599 (1) | 2.95s | OK |  |
| H3#1 | armadilha | Com quantos dias de antecedência preciso avisar a portaria sobre uma … | regulamento_condominio.pdf p.5 | Você precisa avisar a portaria com 48 horas de antecedência sobre uma mudança. | regulamento_condominio.pdf p.5 | sim | sim | nenhum | sim | 0.547 | 0.547 (1) | 2.92s | OK |  |
| H4#1 | negacao | Preciso receber uma advertência antes de levar multa por pagar a taxa… | regulamento_condominio.pdf p.6 | Não, segundo o Art. 23 do regulamento, a multa por atraso no pagamento da taxa condominial (2% sobre o valor devido e juros de 1% ao mês) n… | regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.786 | 0.786 (1) | 3.68s | OK |  |
| H5#1 | negacao | Posso levar meu cachorro para a academia do condomínio? | regulamento_condominio.pdf p.4 | Não, é proibida a permanência de animais na academia. | regulamento_condominio.pdf p.4 | sim | sim | nenhum | sim | 0.635 | 0.635 (1) | 2.55s | OK |  |
| H6#1 | conta | Qual é o valor de cada parcela da reforma da piscina? | ata_assembleia_2026.pdf p.2 | O valor de cada parcela da reforma da piscina é de R$ 7.000,00, calculado a partir do orçamento total de R$ 42.000,00 dividido em 6 parcela… | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.767 | 0.767 (1) | 3.58s | OK |  |
| H7#1 | conta | Quantas unidades não estavam presentes na assembleia de 2026? | ata_assembleia_2026.pdf p.1 | 17 unidades não estavam presentes na assembleia de 2026. | ata_assembleia_2026.pdf p.1 | sim | sim | nenhum | sim | 0.624 | 0.624 (1) | 2.37s | OK |  |
| H8#1 | armadilha | Posso fazer uma obra barulhenta no sábado às 14h? | regulamento_condominio.pdf p.2 | Não, obras barulhentas são permitidas aos sábados apenas das 9h às 13h, conforme o Art. 5º do Capítulo II. As 14h estão fora do horário aut… | regulamento_condominio.pdf p.2 | sim | sim | nenhum | sim | 0.641 | 0.641 (1) | 4.11s | OK |  |
| H9#1 | sem_resposta_plausivel | Qual é o valor da taxa de mudança cobrada pelo condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.650 | — | 3.55s | OK |  |
| H10#1 | sem_resposta | Quem é o zelador do condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.510 | — | 2.39s | OK |  |
| H11#1 | sem_resposta_plausivel | Quantos animais de estimação cada apartamento pode ter? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.729 | — | 2.63s | OK |  |
| H12#1 | sem_resposta_plausivel | Qual era o valor da taxa condominial em 2024? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.648 | — | 3.10s | OK |  |
| H13#1 | conta_combina_arquivos | Se eu danificar de propósito a quadra em junho de 2026, qual é o valo… | regulamento_condominio.pdf p.6, ata_assembleia_2026.pdf p.1 | A multa por danos intencionais às áreas comuns, como a quadra, é equivalente a 3 taxas condominiais mensais vigentes. O valor exato da taxa… | regulamento_condominio.pdf p.6 | sim | sim | 2.040 | sim | 0.522 | 0.522 (1) | 5.28s | FALHA |  |
| H14#1 | direta | Quem representa o Bloco B no conselho fiscal? | ata_assembleia_2026.pdf p.2 | Renata Lima (Bloco B) é a representante do Bloco B no conselho fiscal. | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.504 | 0.504 (1) | 2.27s | OK |  |
| H15#1 | negacao | A síndica atual pode cumprir três mandatos seguidos? | regulamento_condominio.pdf p.1 | A síndica atual pode ser reeleita uma vez, o que permite dois mandatos consecutivos. Não há menção nos documentos sobre a possibilidade de … | regulamento_condominio.pdf p.1 | sim | sim | nenhum | sim | 0.429 | 0.429 (1) | 3.30s | OK |  |
| H16#1 | combina_trechos | Até que horas posso fazer uma festa no salão numa terça-feira, e qual… | regulamento_condominio.pdf p.3 | No salão de festas, os eventos devem terminar até 1h da manhã. Após as 22h, o som deve ser mantido em volume baixo. Essa exceção vale para … | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.710 | 0.710 (1) | 4.37s | OK |  |

## Conferência manual (obrigatória pelo PLANO)

Para cada linha respondida, abrir o PDF na página citada, conferir se o texto sustenta a resposta e escrever OK ou FALHA (com o motivo) na última coluna. As métricas automáticas não substituem esta etapa.
