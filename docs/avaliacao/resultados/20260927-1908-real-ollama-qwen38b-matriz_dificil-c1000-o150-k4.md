# Avaliação DocuMind — real-ollama-qwen38b — 27/09/2026 19:08

## Configuração

- Documentos: regulamento_condominio.pdf, ata_assembleia_2026.pdf
- Trechos: 9 (chunk_size 1000, overlap 150)
- Tempo de indexação: 0.14s
- top_k: 4
- min_score usado: 0.0
- Repetições: 2
- Pausa entre perguntas: 0.0s
- Modelo de geração: qwen3:8b
- Raciocínio (think): ligado
- Modelo de embedding: qwen3-embedding:0.6b
- Perguntas: 16

## Avisos da conferência da matriz

- H6: termo '7.000|7000|sete mil' não aparece nas páginas esperadas.
- H7: termo '17' não aparece nas páginas esperadas.
- H13: termo '2.040|2040' não aparece nas páginas esperadas.

## Métricas agregadas

| Métrica | Valor |
|---|---|
| Execuções (pergunta × repetição) | 32 (erros de API: 0) |
| Resultado OK (todos os critérios) | 26/32 (81%) |
| Acerto de recuperação (alguma evidência no top-4) | 24/24 (100%) |
| Recuperação completa (todas as evidências no top-4) | 24/24 (100%) |
| Citação correta (cita página esperada) | 24/24 (100%) |
| Termos-chave presentes | 18/24 (75%) |
| Recusa nas perguntas sem resposta | 8/8 (100%) |
| Falsa recusa nas respondíveis | 0/24 (0%) |
| Score top-1, respondíveis | n=24, mín 0.428, mediana 0.611, máx 0.786 |
| Score top-1, sem resposta | n=8, mín 0.510, mediana 0.649, máx 0.729 |

### Sugestão de `MIN_SCORE`

- Maior limiar que não recusa nenhuma respondível: **0.428**.
- Margem sobre a sem resposta de maior score: **-0.301**.
- Os scores NÃO separam as classes (a sem resposta mais alta, 0.729, passa a respondível mais baixa, 0.428). O score sozinho não decide a recusa; se usar MIN_SCORE, fique em no máximo 0.428, só como rede de segurança contra perguntas totalmente fora do assunto.

## Resultado por pergunta

Legenda: Rec. = evidência no top-k; Cit. = citou página esperada; Recusa ok = recusou se e só se devia; Pos. = posição da melhor evidência no ranking completo.

| ID | Tipo | Pergunta | Esperado (páginas) | Resposta observada | Páginas citadas | Rec. | Cit. | Termos faltando | Recusa ok | Top-1 | Evid. (pos.) | Tempo | Resultado | Conferência manual |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1#1 | armadilha | Posso usar a churrasqueira até meia-noite numa sexta-feira? | regulamento_condominio.pdf p.3 | Não, a churrasqueira deve ser usada até as 22h. O uso deve terminar até as 22h, conforme Art. 10. Embora os horários de silêncio nas noites… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.594 | 0.594 (1) | 4.11s | OK |  |
| H2#1 | armadilha | Uma criança de 11 anos pode usar a piscina sozinha? | regulamento_condominio.pdf p.3 | Crianças menores de 12 anos só podem usar a piscina acompanhadas de um adulto responsável. Portanto, uma criança de 11 anos não pode usar a… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.599 | 0.599 (1) | 2.22s | OK |  |
| H3#1 | armadilha | Com quantos dias de antecedência preciso avisar a portaria sobre uma … | regulamento_condominio.pdf p.5 | Precisa avisar à portaria com 48 horas de antecedência. | regulamento_condominio.pdf p.5 | sim | sim | nenhum | sim | 0.546 | 0.546 (1) | 1.69s | OK |  |
| H4#1 | negacao | Preciso receber uma advertência antes de levar multa por pagar a taxa… | regulamento_condominio.pdf p.6 | Não, não é necessário receber uma advertência antes de levar multa por pagar a taxa condominial atrasada. De acordo com o regulamento, a mu… | regulamento_condominio.pdf p.6 | sim | sim | 2% | sim | 0.786 | 0.786 (1) | 2.14s | FALHA |  |
| H5#1 | negacao | Posso levar meu cachorro para a academia do condomínio? | regulamento_condominio.pdf p.4 | Não, é proibida a permanência de animais na academia, conforme Art. 17 do Capítulo IV. | regulamento_condominio.pdf p.4 | sim | sim | nenhum | sim | 0.635 | 0.635 (1) | 2.24s | OK |  |
| H6#1 | conta | Qual é o valor de cada parcela da reforma da piscina? | ata_assembleia_2026.pdf p.2 | O valor de cada parcela da reforma da piscina é de R$ 7.000,00. | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.767 | 0.767 (1) | 4.18s | OK |  |
| H7#1 | conta | Quantas unidades não estavam presentes na assembleia de 2026? | ata_assembleia_2026.pdf p.1 | 17 unidades não estavam presentes na assembleia de 2026. | ata_assembleia_2026.pdf p.1 | sim | sim | nenhum | sim | 0.624 | 0.624 (1) | 2.00s | OK |  |
| H8#1 | armadilha | Posso fazer uma obra barulhenta no sábado às 14h? | regulamento_condominio.pdf p.2 | Não, obras com ruído são proibidas no sábado após as 13h, conforme Art. 5º. O horário permitido para obras no sábado é das 9h às 13h. | regulamento_condominio.pdf p.2 | sim | sim | nenhum | sim | 0.642 | 0.642 (1) | 2.53s | OK |  |
| H9#1 | sem_resposta_plausivel | Qual é o valor da taxa de mudança cobrada pelo condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.650 | — | 1.93s | OK |  |
| H10#1 | sem_resposta | Quem é o zelador do condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.510 | — | 1.82s | OK |  |
| H11#1 | sem_resposta_plausivel | Quantos animais de estimação cada apartamento pode ter? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.729 | — | 2.27s | OK |  |
| H12#1 | sem_resposta_plausivel | Qual era o valor da taxa condominial em 2024? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.648 | — | 2.37s | OK |  |
| H13#1 | conta_combina_arquivos | Se eu danificar de propósito a quadra em junho de 2026, qual é o valo… | regulamento_condominio.pdf p.6, ata_assembleia_2026.pdf p.1 | A multa por danos intencionais às áreas comuns, incluindo a quadra, é equivalente a 3 taxas condominiais. Em junho de 2026, a taxa condomin… | ata_assembleia_2026.pdf p.1, regulamento_condominio.pdf p.6 | sim | sim | 2.040 | sim | 0.522 | 0.522 (1) | 4.65s | FALHA |  |
| H14#1 | direta | Quem representa o Bloco B no conselho fiscal? | ata_assembleia_2026.pdf p.2 | Renata Lima | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.504 | 0.504 (1) | 2.30s | OK |  |
| H15#1 | negacao | A síndica pode ser reeleita duas vezes seguidas? | regulamento_condominio.pdf p.1 | Sim, a síndica pode ser reeleita uma vez, ou seja, pode servir até dois mandatos consecutivos. No entanto, não pode ser reeleita para um te… | regulamento_condominio.pdf p.1 | sim | sim | uma reeleição | sim | 0.428 | 0.428 (1) | 4.20s | FALHA |  |
| H16#1 | combina_trechos | Até que horas posso fazer uma festa no salão numa terça-feira, e qual… | regulamento_condominio.pdf p.3 | A festa no salão pode ser realizada até 1h da manhã. Para o som após 22h, a regra é que o som deve ser mantido em volume baixo a partir das… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.710 | 0.710 (1) | 3.07s | OK |  |
| H1#2 | armadilha | Posso usar a churrasqueira até meia-noite numa sexta-feira? | regulamento_condominio.pdf p.3 | Não, a churrasqueira deve ser usada até as 22h. O uso deve terminar até as 22h, conforme Art. 10. Embora os horários de silêncio nas noites… | regulamento_condominio.pdf p.2, regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.594 | 0.594 (1) | 3.67s | OK |  |
| H2#2 | armadilha | Uma criança de 11 anos pode usar a piscina sozinha? | regulamento_condominio.pdf p.3 | Crianças menores de 12 anos só podem usar a piscina acompanhadas de um adulto responsável. Portanto, uma criança de 11 anos não pode usar a… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.599 | 0.599 (1) | 2.18s | OK |  |
| H3#2 | armadilha | Com quantos dias de antecedência preciso avisar a portaria sobre uma … | regulamento_condominio.pdf p.5 | Precisa avisar à portaria com 48 horas de antecedência. | regulamento_condominio.pdf p.5 | sim | sim | nenhum | sim | 0.546 | 0.546 (1) | 1.54s | OK |  |
| H4#2 | negacao | Preciso receber uma advertência antes de levar multa por pagar a taxa… | regulamento_condominio.pdf p.6 | Não, você não recebe uma advertência antes de levar multa por pagar a taxa condominial atrasada. De acordo com o regulamento, a multa por a… | regulamento_condominio.pdf p.6 | sim | sim | 2% | sim | 0.786 | 0.786 (1) | 2.05s | FALHA |  |
| H5#2 | negacao | Posso levar meu cachorro para a academia do condomínio? | regulamento_condominio.pdf p.4 | Não, é proibida a permanência de animais na academia, conforme Art. 17 do Capítulo IV. | regulamento_condominio.pdf p.4 | sim | sim | nenhum | sim | 0.635 | 0.635 (1) | 2.23s | OK |  |
| H6#2 | conta | Qual é o valor de cada parcela da reforma da piscina? | ata_assembleia_2026.pdf p.2 | O valor de cada parcela da reforma da piscina é de R$ 7.000,00. | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.767 | 0.767 (1) | 2.10s | OK |  |
| H7#2 | conta | Quantas unidades não estavam presentes na assembleia de 2026? | ata_assembleia_2026.pdf p.1 | 17 unidades não estavam presentes na assembleia de 2026. | ata_assembleia_2026.pdf p.1 | sim | sim | nenhum | sim | 0.624 | 0.624 (1) | 1.95s | OK |  |
| H8#2 | armadilha | Posso fazer uma obra barulhenta no sábado às 14h? | regulamento_condominio.pdf p.2 | Não, obras com ruído são proibidas aos sábados após as 13h, conforme Art. 5º. | regulamento_condominio.pdf p.2 | sim | sim | nenhum | sim | 0.642 | 0.642 (1) | 1.51s | OK |  |
| H9#2 | sem_resposta_plausivel | Qual é o valor da taxa de mudança cobrada pelo condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.650 | — | 1.90s | OK |  |
| H10#2 | sem_resposta | Quem é o zelador do condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.510 | — | 1.93s | OK |  |
| H11#2 | sem_resposta_plausivel | Quantos animais de estimação cada apartamento pode ter? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.729 | — | 2.25s | OK |  |
| H12#2 | sem_resposta_plausivel | Qual era o valor da taxa condominial em 2024? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.648 | — | 2.36s | OK |  |
| H13#2 | conta_combina_arquivos | Se eu danificar de propósito a quadra em junho de 2026, qual é o valo… | regulamento_condominio.pdf p.6, ata_assembleia_2026.pdf p.1 | A multa por danos intencionais às áreas comuns, incluindo a quadra, é equivalente a 3 taxas condominiais. Em junho de 2026, a taxa condomin… | ata_assembleia_2026.pdf p.1, regulamento_condominio.pdf p.6 | sim | sim | 2.040 | sim | 0.522 | 0.522 (1) | 4.60s | FALHA |  |
| H14#2 | direta | Quem representa o Bloco B no conselho fiscal? | ata_assembleia_2026.pdf p.2 | Renata Lima | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.504 | 0.504 (1) | 2.29s | OK |  |
| H15#2 | negacao | A síndica pode ser reeleita duas vezes seguidas? | regulamento_condominio.pdf p.1 | Sim, a síndica pode ser reeleita uma vez, ou seja, pode servir até dois mandatos consecutivos. No entanto, não pode ser reeleita para um te… | regulamento_condominio.pdf p.1 | sim | sim | uma reeleição | sim | 0.428 | 0.428 (1) | 4.19s | FALHA |  |
| H16#2 | combina_trechos | Até que horas posso fazer uma festa no salão numa terça-feira, e qual… | regulamento_condominio.pdf p.3 | No salão de festas, os eventos devem terminar até 1h da manhã. Para o som após 22h, a regra é que o som deve ser mantido em volume baixo, c… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.710 | 0.710 (1) | 3.00s | OK |  |

## Variação entre repetições

Perguntas cujo resultado, recusa ou páginas citadas mudaram entre as rodadas: H1.

## Conferência manual (obrigatória pelo PLANO)

Para cada linha respondida, abrir o PDF na página citada, conferir se o texto sustenta a resposta e escrever OK ou FALHA (com o motivo) na última coluna. As métricas automáticas não substituem esta etapa.
