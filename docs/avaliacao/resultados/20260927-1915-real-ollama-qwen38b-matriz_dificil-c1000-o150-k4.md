# Avaliação DocuMind — real-ollama-qwen38b — 27/09/2026 19:15

## Configuração

- Documentos: regulamento_condominio.pdf, ata_assembleia_2026.pdf
- Trechos: 9 (chunk_size 1000, overlap 150)
- Tempo de indexação: 0.17s
- top_k: 4
- min_score usado: 0.0
- Repetições: 3
- Pausa entre perguntas: 0.0s
- Modelo de geração: qwen3:8b
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
| Execuções (pergunta × repetição) | 48 (erros de API: 0) |
| Resultado OK (todos os critérios) | 45/48 (94%) |
| Acerto de recuperação (alguma evidência no top-4) | 36/36 (100%) |
| Recuperação completa (todas as evidências no top-4) | 36/36 (100%) |
| Citação correta (cita página esperada) | 36/36 (100%) |
| Termos-chave presentes | 33/36 (92%) |
| Recusa nas perguntas sem resposta | 12/12 (100%) |
| Falsa recusa nas respondíveis | 0/36 (0%) |
| Score top-1, respondíveis | n=36, mín 0.429, mediana 0.610, máx 0.786 |
| Score top-1, sem resposta | n=12, mín 0.510, mediana 0.649, máx 0.729 |

### Sugestão de `MIN_SCORE`

- Maior limiar que não recusa nenhuma respondível: **0.428**.
- Margem sobre a sem resposta de maior score: **-0.301**.
- Os scores NÃO separam as classes (a sem resposta mais alta, 0.729, passa a respondível mais baixa, 0.429). O score sozinho não decide a recusa; se usar MIN_SCORE, fique em no máximo 0.428, só como rede de segurança contra perguntas totalmente fora do assunto.

## Resultado por pergunta

Legenda: Rec. = evidência no top-k; Cit. = citou página esperada; Recusa ok = recusou se e só se devia; Pos. = posição da melhor evidência no ranking completo.

| ID | Tipo | Pergunta | Esperado (páginas) | Resposta observada | Páginas citadas | Rec. | Cit. | Termos faltando | Recusa ok | Top-1 | Evid. (pos.) | Tempo | Resultado | Conferência manual |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1#1 | armadilha | Posso usar a churrasqueira até meia-noite numa sexta-feira? | regulamento_condominio.pdf p.3 | Não, a churrasqueira deve ser utilizada até as 22h, conforme Art. 10. O horário de silêncio nas noites de sexta-feira permite ruído até as … | regulamento_condominio.pdf p.2, regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.595 | 0.595 (1) | 3.42s | OK |  |
| H2#1 | armadilha | Uma criança de 11 anos pode usar a piscina sozinha? | regulamento_condominio.pdf p.3 | Crianças menores de 12 anos só podem usar a piscina acompanhadas de um adulto responsável. Portanto, uma criança de 11 anos não pode usar a… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.597 | 0.597 (1) | 2.17s | OK |  |
| H3#1 | armadilha | Com quantos dias de antecedência preciso avisar a portaria sobre uma … | regulamento_condominio.pdf p.5 | Precisa avisar à portaria com 48 horas de antecedência. | regulamento_condominio.pdf p.5 | sim | sim | nenhum | sim | 0.547 | 0.547 (1) | 1.52s | OK |  |
| H4#1 | negacao | Preciso receber uma advertência antes de levar multa por pagar a taxa… | regulamento_condominio.pdf p.6 | Não, não é necessário receber uma advertência antes de levar multa por pagar a taxa condominial atrasada. A multa por atraso não depende de… | regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.786 | 0.786 (1) | 1.96s | OK |  |
| H5#1 | negacao | Posso levar meu cachorro para a academia do condomínio? | regulamento_condominio.pdf p.4 | Não, é proibido a permanência de animais na academia, conforme Art. 17 do Capítulo IV. | regulamento_condominio.pdf p.4 | sim | sim | nenhum | sim | 0.635 | 0.635 (1) | 3.09s | OK |  |
| H6#1 | conta | Qual é o valor de cada parcela da reforma da piscina? | ata_assembleia_2026.pdf p.2 | Cada parcela da reforma da piscina tem o valor de R$ 7.000,00. | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.767 | 0.767 (1) | 2.33s | OK |  |
| H7#1 | conta | Quantas unidades não estavam presentes na assembleia de 2026? | ata_assembleia_2026.pdf p.1 | Foram 17 unidades que não estavam presentes na assembleia de 2026. | ata_assembleia_2026.pdf p.1 | sim | sim | nenhum | sim | 0.624 | 0.624 (1) | 1.84s | OK |  |
| H8#1 | armadilha | Posso fazer uma obra barulhenta no sábado às 14h? | regulamento_condominio.pdf p.2 | Não, obras com ruído são proibidas aos sábados após as 13h. | regulamento_condominio.pdf p.2 | sim | sim | nenhum | sim | 0.641 | 0.641 (1) | 2.27s | OK |  |
| H9#1 | sem_resposta_plausivel | Qual é o valor da taxa de mudança cobrada pelo condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.650 | — | 2.23s | OK |  |
| H10#1 | sem_resposta | Quem é o zelador do condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.510 | — | 2.07s | OK |  |
| H11#1 | sem_resposta_plausivel | Quantos animais de estimação cada apartamento pode ter? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.729 | — | 2.13s | OK |  |
| H12#1 | sem_resposta_plausivel | Qual era o valor da taxa condominial em 2024? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.648 | — | 2.59s | OK |  |
| H13#1 | conta_combina_arquivos | Se eu danificar de propósito a quadra em junho de 2026, qual é o valo… | regulamento_condominio.pdf p.6, ata_assembleia_2026.pdf p.1 | A multa por danos intencionais às áreas comuns, como a quadra, é equivalente a 3 taxas condominiais. Como a taxa foi reajustada para R$ 680… | ata_assembleia_2026.pdf p.1, regulamento_condominio.pdf p.6 | sim | sim | 2.040 | sim | 0.521 | 0.521 (1) | 4.07s | FALHA |  |
| H14#1 | direta | Quem representa o Bloco B no conselho fiscal? | ata_assembleia_2026.pdf p.2 | Renata Lima | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.504 | 0.504 (1) | 2.31s | OK |  |
| H15#1 | negacao | A síndica atual pode cumprir três mandatos seguidos? | regulamento_condominio.pdf p.1 | De acordo com o regulamento, a síndica atual pode ser reeleita uma vez, o que permite um total de dois mandatos. Portanto, não é permitido … | regulamento_condominio.pdf p.1 | sim | sim | nenhum | sim | 0.429 | 0.429 (1) | 2.59s | OK |  |
| H16#1 | combina_trechos | Até que horas posso fazer uma festa no salão numa terça-feira, e qual… | regulamento_condominio.pdf p.3 | A festa no salão pode ser realizada até 1h da manhã, independentemente do dia da semana. Para o som após as 22h, o regulamento estabelece q… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.710 | 0.710 (1) | 3.67s | OK |  |
| H1#2 | armadilha | Posso usar a churrasqueira até meia-noite numa sexta-feira? | regulamento_condominio.pdf p.3 | Não, você não pode usar a churrasqueira até meia-noite numa sexta-feira. O uso da churrasqueira deve terminar até as 22h, conforme Art. 10.… | regulamento_condominio.pdf p.2, regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.595 | 0.595 (1) | 4.13s | OK |  |
| H2#2 | armadilha | Uma criança de 11 anos pode usar a piscina sozinha? | regulamento_condominio.pdf p.3 | Crianças menores de 12 anos só podem usar a piscina acompanhadas de um adulto responsável. Portanto, uma criança de 11 anos não pode usar a… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.597 | 0.597 (1) | 2.22s | OK |  |
| H3#2 | armadilha | Com quantos dias de antecedência preciso avisar a portaria sobre uma … | regulamento_condominio.pdf p.5 | Precisa avisar à portaria com 48 horas de antecedência. | regulamento_condominio.pdf p.5 | sim | sim | nenhum | sim | 0.547 | 0.547 (1) | 1.51s | OK |  |
| H4#2 | negacao | Preciso receber uma advertência antes de levar multa por pagar a taxa… | regulamento_condominio.pdf p.6 | Não, você não recebe uma advertência antes de levar multa por pagar a taxa condominial atrasada. De acordo com o regulamento, a multa por a… | regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.786 | 0.786 (1) | 1.99s | OK |  |
| H5#2 | negacao | Posso levar meu cachorro para a academia do condomínio? | regulamento_condominio.pdf p.4 | Não, é proibida a permanência de animais na academia, conforme estabelecido no Art. 17 do Capítulo IV. | regulamento_condominio.pdf p.4 | sim | sim | nenhum | sim | 0.635 | 0.635 (1) | 2.44s | OK |  |
| H6#2 | conta | Qual é o valor de cada parcela da reforma da piscina? | ata_assembleia_2026.pdf p.2 | Cada parcela da reforma da piscina tem o valor de R$ 7.000,00. | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.767 | 0.767 (1) | 2.34s | OK |  |
| H7#2 | conta | Quantas unidades não estavam presentes na assembleia de 2026? | ata_assembleia_2026.pdf p.1 | Foram 17 unidades que não estavam presentes na assembleia de 2026. | ata_assembleia_2026.pdf p.1 | sim | sim | nenhum | sim | 0.624 | 0.624 (1) | 1.86s | OK |  |
| H8#2 | armadilha | Posso fazer uma obra barulhenta no sábado às 14h? | regulamento_condominio.pdf p.2 | Não, obras com ruído são proibidas aos sábados após as 13h. | regulamento_condominio.pdf p.2 | sim | sim | nenhum | sim | 0.641 | 0.641 (1) | 2.29s | OK |  |
| H9#2 | sem_resposta_plausivel | Qual é o valor da taxa de mudança cobrada pelo condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.650 | — | 2.20s | OK |  |
| H10#2 | sem_resposta | Quem é o zelador do condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.510 | — | 2.14s | OK |  |
| H11#2 | sem_resposta_plausivel | Quantos animais de estimação cada apartamento pode ter? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.729 | — | 2.12s | OK |  |
| H12#2 | sem_resposta_plausivel | Qual era o valor da taxa condominial em 2024? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.648 | — | 2.58s | OK |  |
| H13#2 | conta_combina_arquivos | Se eu danificar de propósito a quadra em junho de 2026, qual é o valo… | regulamento_condominio.pdf p.6, ata_assembleia_2026.pdf p.1 | A multa por danos intencionais às áreas comuns, como a quadra, é equivalente a 3 taxas condominiais. Como a taxa foi reajustada para R$ 680… | ata_assembleia_2026.pdf p.1, regulamento_condominio.pdf p.6 | sim | sim | 2.040 | sim | 0.521 | 0.521 (1) | 4.05s | FALHA |  |
| H14#2 | direta | Quem representa o Bloco B no conselho fiscal? | ata_assembleia_2026.pdf p.2 | Renata Lima | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.504 | 0.504 (1) | 2.35s | OK |  |
| H15#2 | negacao | A síndica atual pode cumprir três mandatos seguidos? | regulamento_condominio.pdf p.1 | De acordo com o regulamento, a síndica atual pode ser reeleita uma vez, o que permite um total de dois mandatos. Portanto, não é permitido … | regulamento_condominio.pdf p.1 | sim | sim | nenhum | sim | 0.429 | 0.429 (1) | 2.61s | OK |  |
| H16#2 | combina_trechos | Até que horas posso fazer uma festa no salão numa terça-feira, e qual… | regulamento_condominio.pdf p.3 | No salão de festas, eventos são permitidos até 1h da manhã. Para o som depois das 22h, a regra é que o volume deve ser mantido em nível bai… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.710 | 0.710 (1) | 4.06s | OK |  |
| H1#3 | armadilha | Posso usar a churrasqueira até meia-noite numa sexta-feira? | regulamento_condominio.pdf p.3 | Não, você não pode usar a churrasqueira até meia-noite numa sexta-feira. O uso da churrasqueira deve terminar até as 22h, conforme Art. 10.… | regulamento_condominio.pdf p.2, regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.595 | 0.595 (1) | 4.14s | OK |  |
| H2#3 | armadilha | Uma criança de 11 anos pode usar a piscina sozinha? | regulamento_condominio.pdf p.3 | Crianças menores de 12 anos só podem usar a piscina acompanhadas de um adulto responsável. Portanto, uma criança de 11 anos não pode usar a… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.597 | 0.597 (1) | 2.08s | OK |  |
| H3#3 | armadilha | Com quantos dias de antecedência preciso avisar a portaria sobre uma … | regulamento_condominio.pdf p.5 | Precisa avisar à portaria com 48 horas de antecedência. | regulamento_condominio.pdf p.5 | sim | sim | nenhum | sim | 0.547 | 0.547 (1) | 1.52s | OK |  |
| H4#3 | negacao | Preciso receber uma advertência antes de levar multa por pagar a taxa… | regulamento_condominio.pdf p.6 | Não, você não recebe uma advertência antes de levar multa por pagar a taxa condominial atrasada. De acordo com o regulamento, a multa por a… | regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.786 | 0.786 (1) | 1.99s | OK |  |
| H5#3 | negacao | Posso levar meu cachorro para a academia do condomínio? | regulamento_condominio.pdf p.4 | Não, é proibida a permanência de animais na academia, conforme estabelecido no Art. 17 do Capítulo IV. | regulamento_condominio.pdf p.4 | sim | sim | nenhum | sim | 0.635 | 0.635 (1) | 2.43s | OK |  |
| H6#3 | conta | Qual é o valor de cada parcela da reforma da piscina? | ata_assembleia_2026.pdf p.2 | Cada parcela da reforma da piscina tem o valor de R$ 7.000,00. | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.767 | 0.767 (1) | 2.33s | OK |  |
| H7#3 | conta | Quantas unidades não estavam presentes na assembleia de 2026? | ata_assembleia_2026.pdf p.1 | Foram 17 unidades que não estavam presentes na assembleia de 2026. | ata_assembleia_2026.pdf p.1 | sim | sim | nenhum | sim | 0.624 | 0.624 (1) | 1.84s | OK |  |
| H8#3 | armadilha | Posso fazer uma obra barulhenta no sábado às 14h? | regulamento_condominio.pdf p.2 | Não, obras com ruído são proibidas aos sábados após as 13h. | regulamento_condominio.pdf p.2 | sim | sim | nenhum | sim | 0.641 | 0.641 (1) | 2.28s | OK |  |
| H9#3 | sem_resposta_plausivel | Qual é o valor da taxa de mudança cobrada pelo condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.650 | — | 2.21s | OK |  |
| H10#3 | sem_resposta | Quem é o zelador do condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.510 | — | 2.14s | OK |  |
| H11#3 | sem_resposta_plausivel | Quantos animais de estimação cada apartamento pode ter? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.729 | — | 2.12s | OK |  |
| H12#3 | sem_resposta_plausivel | Qual era o valor da taxa condominial em 2024? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.648 | — | 2.59s | OK |  |
| H13#3 | conta_combina_arquivos | Se eu danificar de propósito a quadra em junho de 2026, qual é o valo… | regulamento_condominio.pdf p.6, ata_assembleia_2026.pdf p.1 | A multa por danos intencionais às áreas comuns, como a quadra, é equivalente a 3 taxas condominiais. Como a taxa foi reajustada para R$ 680… | ata_assembleia_2026.pdf p.1, regulamento_condominio.pdf p.6 | sim | sim | 2.040 | sim | 0.521 | 0.521 (1) | 4.05s | FALHA |  |
| H14#3 | direta | Quem representa o Bloco B no conselho fiscal? | ata_assembleia_2026.pdf p.2 | Renata Lima | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.504 | 0.504 (1) | 2.31s | OK |  |
| H15#3 | negacao | A síndica atual pode cumprir três mandatos seguidos? | regulamento_condominio.pdf p.1 | De acordo com o regulamento, a síndica atual pode ser reeleita uma vez, o que permite um total de dois mandatos. Portanto, não é permitido … | regulamento_condominio.pdf p.1 | sim | sim | nenhum | sim | 0.429 | 0.429 (1) | 2.59s | OK |  |
| H16#3 | combina_trechos | Até que horas posso fazer uma festa no salão numa terça-feira, e qual… | regulamento_condominio.pdf p.3 | No salão de festas, eventos são permitidos até 1h da manhã. Para o som depois das 22h, a regra é que o volume deve ser mantido em nível bai… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.710 | 0.710 (1) | 4.04s | OK |  |

## Variação entre repetições

Perguntas cujo resultado, recusa ou páginas citadas mudaram entre as rodadas: nenhuma.

## Conferência manual (obrigatória pelo PLANO)

Para cada linha respondida, abrir o PDF na página citada, conferir se o texto sustenta a resposta e escrever OK ou FALHA (com o motivo) na última coluna. As métricas automáticas não substituem esta etapa.
