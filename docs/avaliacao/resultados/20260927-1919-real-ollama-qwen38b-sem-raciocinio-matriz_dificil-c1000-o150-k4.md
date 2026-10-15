# Avaliação DocuMind — real-ollama-qwen38b-sem-raciocinio — 27/09/2026 19:19

## Configuração

- Documentos: regulamento_condominio.pdf, ata_assembleia_2026.pdf
- Trechos: 9 (chunk_size 1000, overlap 150)
- Tempo de indexação: 0.18s
- top_k: 4
- min_score usado: 0.0
- Repetições: 3
- Pausa entre perguntas: 0.0s
- Modelo de geração: qwen3:8b
- Raciocínio (think): desligado
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
| Execuções (pergunta × repetição) | 48 (erros de API: 0) |
| Resultado OK (todos os critérios) | 35/48 (73%) |
| Acerto de recuperação (alguma evidência no top-4) | 36/36 (100%) |
| Recuperação completa (todas as evidências no top-4) | 36/36 (100%) |
| Citação correta (cita página esperada) | 36/36 (100%) |
| Termos-chave presentes | 23/36 (64%) |
| Recusa nas perguntas sem resposta | 12/12 (100%) |
| Falsa recusa nas respondíveis | 0/36 (0%) |
| Score top-1, respondíveis | n=36, mín 0.429, mediana 0.611, máx 0.786 |
| Score top-1, sem resposta | n=12, mín 0.510, mediana 0.649, máx 0.729 |

### Sugestão de `MIN_SCORE`

- Maior limiar que não recusa nenhuma respondível: **0.428**.
- Margem sobre a sem resposta de maior score: **-0.301**.
- Os scores NÃO separam as classes (a sem resposta mais alta, 0.729, passa a respondível mais baixa, 0.429). O score sozinho não decide a recusa; se usar MIN_SCORE, fique em no máximo 0.428, só como rede de segurança contra perguntas totalmente fora do assunto.

## Resultado por pergunta

Legenda: Rec. = evidência no top-k; Cit. = citou página esperada; Recusa ok = recusou se e só se devia; Pos. = posição da melhor evidência no ranking completo.

| ID | Tipo | Pergunta | Esperado (páginas) | Resposta observada | Páginas citadas | Rec. | Cit. | Termos faltando | Recusa ok | Top-1 | Evid. (pos.) | Tempo | Resultado | Conferência manual |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1#1 | armadilha | Posso usar a churrasqueira até meia-noite numa sexta-feira? | regulamento_condominio.pdf p.3 | Sim, você pode usar a churrasqueira até meia-noite numa sexta-feira. | regulamento_condominio.pdf p.3 | sim | sim | 22h | sim | 0.594 | 0.594 (1) | 11.05s | FALHA |  |
| H2#1 | armadilha | Uma criança de 11 anos pode usar a piscina sozinha? | regulamento_condominio.pdf p.3 | Não, uma criança de 11 anos não pode usar a piscina sozinha. Crianças menores de 12 anos só podem usar a piscina acompanhadas de um adulto … | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.599 | 0.599 (1) | 1.65s | OK |  |
| H3#1 | armadilha | Com quantos dias de antecedência preciso avisar a portaria sobre uma … | regulamento_condominio.pdf p.5 | Precisa avisar a portaria com 48 horas de antecedência. | regulamento_condominio.pdf p.5 | sim | sim | nenhum | sim | 0.550 | 0.550 (1) | 0.49s | OK |  |
| H4#1 | negacao | Preciso receber uma advertência antes de levar multa por pagar a taxa… | regulamento_condominio.pdf p.6 | Não, você não precisa receber uma advertência antes de levar multa por pagar a taxa condominial atrasada. A multa por atraso não depende de… | regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.786 | 0.786 (1) | 0.66s | OK |  |
| H5#1 | negacao | Posso levar meu cachorro para a academia do condomínio? | regulamento_condominio.pdf p.4 | Não, é proibida a permanência de animais na academia. | regulamento_condominio.pdf p.4 | sim | sim | nenhum | sim | 0.635 | 0.635 (1) | 0.48s | OK |  |
| H6#1 | conta | Qual é o valor de cada parcela da reforma da piscina? | ata_assembleia_2026.pdf p.2 | O orçamento da reforma da piscina é de R$ 42.000,00, pago em 6 parcelas mensais. | ata_assembleia_2026.pdf p.2 | sim | sim | 7.000 | sim | 0.767 | 0.767 (1) | 3.09s | FALHA |  |
| H7#1 | conta | Quantas unidades não estavam presentes na assembleia de 2026? | ata_assembleia_2026.pdf p.1 | Havia 17 unidades não presentes na assembleia de 2026. | ata_assembleia_2026.pdf p.1 | sim | sim | nenhum | sim | 0.624 | 0.624 (1) | 0.48s | OK |  |
| H8#1 | armadilha | Posso fazer uma obra barulhenta no sábado às 14h? | regulamento_condominio.pdf p.2 | Sim, você pode fazer uma obra barulhenta no sábado às 14h. | regulamento_condominio.pdf p.2 | sim | sim | 13h | sim | 0.641 | 0.641 (1) | 0.53s | FALHA |  |
| H9#1 | sem_resposta_plausivel | Qual é o valor da taxa de mudança cobrada pelo condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.650 | — | 0.32s | OK |  |
| H10#1 | sem_resposta | Quem é o zelador do condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.510 | — | 0.32s | OK |  |
| H11#1 | sem_resposta_plausivel | Quantos animais de estimação cada apartamento pode ter? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.729 | — | 0.30s | OK |  |
| H12#1 | sem_resposta_plausivel | Qual era o valor da taxa condominial em 2024? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.648 | — | 0.26s | OK |  |
| H13#1 | conta_combina_arquivos | Se eu danificar de propósito a quadra em junho de 2026, qual é o valo… | regulamento_condominio.pdf p.6, ata_assembleia_2026.pdf p.1 | A multa por danos intencionais às áreas comuns é equivalente a 3 taxas condominiais. | regulamento_condominio.pdf p.6 | sim | sim | 2.040 | sim | 0.521 | 0.521 (1) | 0.54s | FALHA |  |
| H14#1 | direta | Quem representa o Bloco B no conselho fiscal? | ata_assembleia_2026.pdf p.2 | Renata Lima | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.504 | 0.504 (1) | 0.39s | OK |  |
| H15#1 | negacao | A síndica atual pode cumprir três mandatos seguidos? | regulamento_condominio.pdf p.1 | A síndica atual pode cumprir dois mandatos seguidos. | regulamento_condominio.pdf p.1 | sim | sim | não | sim | 0.429 | 0.429 (1) | 0.47s | FALHA |  |
| H16#1 | combina_trechos | Até que horas posso fazer uma festa no salão numa terça-feira, e qual… | regulamento_condominio.pdf p.3 | No salão de festas, os eventos podem terminar até 1h da manhã. Para o som depois das 22h, a regra é que o som deve ser mantido em volume ba… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.710 | 0.710 (1) | 0.71s | OK |  |
| H1#2 | armadilha | Posso usar a churrasqueira até meia-noite numa sexta-feira? | regulamento_condominio.pdf p.3 | Sim, você pode usar a churrasqueira até meia-noite numa sexta-feira. | regulamento_condominio.pdf p.3 | sim | sim | 22h | sim | 0.594 | 0.594 (1) | 0.38s | FALHA |  |
| H2#2 | armadilha | Uma criança de 11 anos pode usar a piscina sozinha? | regulamento_condominio.pdf p.3 | Não, uma criança de 11 anos não pode usar a piscina sozinha. Crianças menores de 12 anos só podem usar a piscina acompanhadas de um adulto … | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.599 | 0.599 (1) | 0.57s | OK |  |
| H3#2 | armadilha | Com quantos dias de antecedência preciso avisar a portaria sobre uma … | regulamento_condominio.pdf p.5 | Precisa avisar a portaria com 48 horas de antecedência. | regulamento_condominio.pdf p.5 | sim | sim | nenhum | sim | 0.550 | 0.550 (1) | 0.37s | OK |  |
| H4#2 | negacao | Preciso receber uma advertência antes de levar multa por pagar a taxa… | regulamento_condominio.pdf p.6 | Não, você não precisa receber uma advertência antes de levar multa por pagar a taxa condominial atrasada. A multa por atraso não depende de… | regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.786 | 0.786 (1) | 0.62s | OK |  |
| H5#2 | negacao | Posso levar meu cachorro para a academia do condomínio? | regulamento_condominio.pdf p.4 | Não, é proibida a permanência de animais na academia. | regulamento_condominio.pdf p.4 | sim | sim | nenhum | sim | 0.635 | 0.635 (1) | 0.47s | OK |  |
| H6#2 | conta | Qual é o valor de cada parcela da reforma da piscina? | ata_assembleia_2026.pdf p.2 | O valor de cada parcela da reforma da piscina é de R$ 7.000,00. | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.767 | 0.767 (1) | 0.53s | OK |  |
| H7#2 | conta | Quantas unidades não estavam presentes na assembleia de 2026? | ata_assembleia_2026.pdf p.1 | Havia 17 unidades não presentes na assembleia de 2026. | ata_assembleia_2026.pdf p.1 | sim | sim | nenhum | sim | 0.624 | 0.624 (1) | 0.46s | OK |  |
| H8#2 | armadilha | Posso fazer uma obra barulhenta no sábado às 14h? | regulamento_condominio.pdf p.2 | Sim, você pode fazer uma obra barulhenta no sábado às 14h. | regulamento_condominio.pdf p.2 | sim | sim | 13h | sim | 0.641 | 0.641 (1) | 0.39s | FALHA |  |
| H9#2 | sem_resposta_plausivel | Qual é o valor da taxa de mudança cobrada pelo condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.650 | — | 0.31s | OK |  |
| H10#2 | sem_resposta | Quem é o zelador do condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.510 | — | 0.29s | OK |  |
| H11#2 | sem_resposta_plausivel | Quantos animais de estimação cada apartamento pode ter? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.729 | — | 0.29s | OK |  |
| H12#2 | sem_resposta_plausivel | Qual era o valor da taxa condominial em 2024? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.648 | — | 0.27s | OK |  |
| H13#2 | conta_combina_arquivos | Se eu danificar de propósito a quadra em junho de 2026, qual é o valo… | regulamento_condominio.pdf p.6, ata_assembleia_2026.pdf p.1 | A multa por danos intencionais às áreas comuns é equivalente a 3 taxas condominiais. | regulamento_condominio.pdf p.6 | sim | sim | 2.040 | sim | 0.521 | 0.521 (1) | 0.55s | FALHA |  |
| H14#2 | direta | Quem representa o Bloco B no conselho fiscal? | ata_assembleia_2026.pdf p.2 | Renata Lima | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.504 | 0.504 (1) | 0.39s | OK |  |
| H15#2 | negacao | A síndica atual pode cumprir três mandatos seguidos? | regulamento_condominio.pdf p.1 | A síndica atual pode cumprir dois mandatos seguidos. | regulamento_condominio.pdf p.1 | sim | sim | não | sim | 0.429 | 0.429 (1) | 0.47s | FALHA |  |
| H16#2 | combina_trechos | Até que horas posso fazer uma festa no salão numa terça-feira, e qual… | regulamento_condominio.pdf p.3 | No salão de festas, os eventos podem terminar até 1h da manhã. Para o som depois das 22h, a regra é que o som deve ser mantido em volume ba… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.710 | 0.710 (1) | 0.71s | OK |  |
| H1#3 | armadilha | Posso usar a churrasqueira até meia-noite numa sexta-feira? | regulamento_condominio.pdf p.3 | Sim, você pode usar a churrasqueira até meia-noite numa sexta-feira. | regulamento_condominio.pdf p.3 | sim | sim | 22h | sim | 0.594 | 0.594 (1) | 0.39s | FALHA |  |
| H2#3 | armadilha | Uma criança de 11 anos pode usar a piscina sozinha? | regulamento_condominio.pdf p.3 | Não, uma criança de 11 anos não pode usar a piscina sozinha. Crianças menores de 12 anos só podem usar a piscina acompanhadas de um adulto … | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.599 | 0.599 (1) | 0.58s | OK |  |
| H3#3 | armadilha | Com quantos dias de antecedência preciso avisar a portaria sobre uma … | regulamento_condominio.pdf p.5 | Precisa avisar a portaria com 48 horas de antecedência. | regulamento_condominio.pdf p.5 | sim | sim | nenhum | sim | 0.550 | 0.550 (1) | 0.37s | OK |  |
| H4#3 | negacao | Preciso receber uma advertência antes de levar multa por pagar a taxa… | regulamento_condominio.pdf p.6 | Não, você não precisa receber uma advertência antes de levar multa por pagar a taxa condominial atrasada. A multa por atraso não depende de… | regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.786 | 0.786 (1) | 0.63s | OK |  |
| H5#3 | negacao | Posso levar meu cachorro para a academia do condomínio? | regulamento_condominio.pdf p.4 | Não, é proibida a permanência de animais na academia. | regulamento_condominio.pdf p.4 | sim | sim | nenhum | sim | 0.635 | 0.635 (1) | 0.47s | OK |  |
| H6#3 | conta | Qual é o valor de cada parcela da reforma da piscina? | ata_assembleia_2026.pdf p.2 | O valor de cada parcela da reforma da piscina é de R$ 7.000,00. | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.767 | 0.767 (1) | 0.54s | OK |  |
| H7#3 | conta | Quantas unidades não estavam presentes na assembleia de 2026? | ata_assembleia_2026.pdf p.1 | Havia 17 unidades não presentes na assembleia de 2026. | ata_assembleia_2026.pdf p.1 | sim | sim | nenhum | sim | 0.624 | 0.624 (1) | 0.46s | OK |  |
| H8#3 | armadilha | Posso fazer uma obra barulhenta no sábado às 14h? | regulamento_condominio.pdf p.2 | Sim, você pode fazer uma obra barulhenta no sábado às 14h. | regulamento_condominio.pdf p.2 | sim | sim | 13h | sim | 0.641 | 0.641 (1) | 0.38s | FALHA |  |
| H9#3 | sem_resposta_plausivel | Qual é o valor da taxa de mudança cobrada pelo condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.650 | — | 0.30s | OK |  |
| H10#3 | sem_resposta | Quem é o zelador do condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.510 | — | 0.30s | OK |  |
| H11#3 | sem_resposta_plausivel | Quantos animais de estimação cada apartamento pode ter? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.729 | — | 0.29s | OK |  |
| H12#3 | sem_resposta_plausivel | Qual era o valor da taxa condominial em 2024? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.648 | — | 0.26s | OK |  |
| H13#3 | conta_combina_arquivos | Se eu danificar de propósito a quadra em junho de 2026, qual é o valo… | regulamento_condominio.pdf p.6, ata_assembleia_2026.pdf p.1 | A multa por danos intencionais às áreas comuns é equivalente a 3 taxas condominiais. | regulamento_condominio.pdf p.6 | sim | sim | 2.040 | sim | 0.521 | 0.521 (1) | 0.54s | FALHA |  |
| H14#3 | direta | Quem representa o Bloco B no conselho fiscal? | ata_assembleia_2026.pdf p.2 | Renata Lima | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.504 | 0.504 (1) | 0.38s | OK |  |
| H15#3 | negacao | A síndica atual pode cumprir três mandatos seguidos? | regulamento_condominio.pdf p.1 | A síndica atual pode cumprir dois mandatos seguidos. | regulamento_condominio.pdf p.1 | sim | sim | não | sim | 0.429 | 0.429 (1) | 0.47s | FALHA |  |
| H16#3 | combina_trechos | Até que horas posso fazer uma festa no salão numa terça-feira, e qual… | regulamento_condominio.pdf p.3 | No salão de festas, os eventos podem terminar até 1h da manhã. Para o som depois das 22h, a regra é que o som deve ser mantido em volume ba… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.710 | 0.710 (1) | 0.70s | OK |  |

## Variação entre repetições

Perguntas cujo resultado, recusa ou páginas citadas mudaram entre as rodadas: H6.

## Conferência manual (obrigatória pelo PLANO)

Para cada linha respondida, abrir o PDF na página citada, conferir se o texto sustenta a resposta e escrever OK ou FALHA (com o motivo) na última coluna. As métricas automáticas não substituem esta etapa.
