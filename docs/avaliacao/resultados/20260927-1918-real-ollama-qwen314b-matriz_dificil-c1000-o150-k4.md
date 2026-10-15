# Avaliação DocuMind — real-ollama-qwen314b — 27/09/2026 19:18

## Configuração

- Documentos: regulamento_condominio.pdf, ata_assembleia_2026.pdf
- Trechos: 9 (chunk_size 1000, overlap 150)
- Tempo de indexação: 0.13s
- top_k: 4
- min_score usado: 0.0
- Repetições: 3
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
| Execuções (pergunta × repetição) | 48 (erros de API: 0) |
| Resultado OK (todos os critérios) | 48/48 (100%) |
| Acerto de recuperação (alguma evidência no top-4) | 36/36 (100%) |
| Recuperação completa (todas as evidências no top-4) | 36/36 (100%) |
| Citação correta (cita página esperada) | 36/36 (100%) |
| Termos-chave presentes | 36/36 (100%) |
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
| H1#1 | armadilha | Posso usar a churrasqueira até meia-noite numa sexta-feira? | regulamento_condominio.pdf p.3 | Não, a churrasqueira deve ser devolvida até as 22h, conforme determinado no Art. 10. Não há menção a extensão do horário para meia-noite em… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.595 | 0.595 (1) | 22.50s | OK |  |
| H2#1 | armadilha | Uma criança de 11 anos pode usar a piscina sozinha? | regulamento_condominio.pdf p.3 | Não, crianças menores de 12 anos só podem usar a piscina acompanhadas de um adulto responsável. | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.597 | 0.597 (1) | 5.23s | OK |  |
| H3#1 | armadilha | Com quantos dias de antecedência preciso avisar a portaria sobre uma … | regulamento_condominio.pdf p.5 | Você precisa avisar a portaria com 48 horas de antecedência sobre uma mudança. | regulamento_condominio.pdf p.5 | sim | sim | nenhum | sim | 0.547 | 0.547 (1) | 3.24s | OK |  |
| H4#1 | negacao | Preciso receber uma advertência antes de levar multa por pagar a taxa… | regulamento_condominio.pdf p.6 | Não, segundo o regulamento, a multa por atraso no pagamento da taxa condominial não depende de advertência prévia. | regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.786 | 0.786 (1) | 3.32s | OK |  |
| H5#1 | negacao | Posso levar meu cachorro para a academia do condomínio? | regulamento_condominio.pdf p.4 | Não, é proibida a permanência de animais na academia. | regulamento_condominio.pdf p.4 | sim | sim | nenhum | sim | 0.635 | 0.635 (1) | 2.57s | OK |  |
| H6#1 | conta | Qual é o valor de cada parcela da reforma da piscina? | ata_assembleia_2026.pdf p.2 | O valor de cada parcela da reforma da piscina é de R$ 7.000,00, pois o orçamento total de R$ 42.000,00 será pago em 6 parcelas mensais. | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.767 | 0.767 (1) | 3.89s | OK |  |
| H7#1 | conta | Quantas unidades não estavam presentes na assembleia de 2026? | ata_assembleia_2026.pdf p.1 | 17 unidades não estavam presentes na assembleia de 2026. | ata_assembleia_2026.pdf p.1 | sim | sim | nenhum | sim | 0.624 | 0.624 (1) | 3.42s | OK |  |
| H8#1 | armadilha | Posso fazer uma obra barulhenta no sábado às 14h? | regulamento_condominio.pdf p.2 | Não, obras com ruído são permitidas aos sábados apenas das 9h às 13h, conforme o Art. 5º do Capítulo II. As 14h ultrapassam esse horário es… | regulamento_condominio.pdf p.2 | sim | sim | nenhum | sim | 0.643 | 0.643 (1) | 3.71s | OK |  |
| H9#1 | sem_resposta_plausivel | Qual é o valor da taxa de mudança cobrada pelo condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.650 | — | 3.60s | OK |  |
| H10#1 | sem_resposta | Quem é o zelador do condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.510 | — | 2.45s | OK |  |
| H11#1 | sem_resposta_plausivel | Quantos animais de estimação cada apartamento pode ter? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.729 | — | 3.85s | OK |  |
| H12#1 | sem_resposta_plausivel | Qual era o valor da taxa condominial em 2024? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.648 | — | 4.54s | OK |  |
| H13#1 | conta_combina_arquivos | Se eu danificar de propósito a quadra em junho de 2026, qual é o valo… | regulamento_condominio.pdf p.6, ata_assembleia_2026.pdf p.1 | A multa por danos intencionais à quadra em junho de 2026 corresponde a 3 taxas condominiais mensais vigentes. Conforme a ata da assembleia … | ata_assembleia_2026.pdf p.1, regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.521 | 0.521 (1) | 12.96s | OK |  |
| H14#1 | direta | Quem representa o Bloco B no conselho fiscal? | ata_assembleia_2026.pdf p.2 | Renata Lima representa o Bloco B no conselho fiscal. | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.504 | 0.504 (1) | 3.19s | OK |  |
| H15#1 | negacao | A síndica atual pode cumprir três mandatos seguidos? | regulamento_condominio.pdf p.1 | Não, a síndica atual não pode cumprir três mandatos seguidos. O mandato da síndica é de 2 anos, com permitida uma reeleição, o que totaliza… | regulamento_condominio.pdf p.1 | sim | sim | nenhum | sim | 0.429 | 0.429 (1) | 4.32s | OK |  |
| H16#1 | combina_trechos | Até que horas posso fazer uma festa no salão numa terça-feira, e qual… | regulamento_condominio.pdf p.3 | No salão de festas, os eventos podem terminar até 1h da manhã. Após as 22h, o som deve ser mantido em volume baixo, conforme exceção ao hor… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.710 | 0.710 (1) | 5.79s | OK |  |
| H1#2 | armadilha | Posso usar a churrasqueira até meia-noite numa sexta-feira? | regulamento_condominio.pdf p.3 | Sim, a churrasqueira pode ser usada até 22h, conforme estabelecido no Art. 10 do Capítulo III. Não consta nos documentos que o horário poss… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.595 | 0.595 (1) | 5.22s | OK |  |
| H2#2 | armadilha | Uma criança de 11 anos pode usar a piscina sozinha? | regulamento_condominio.pdf p.3 | Não, crianças menores de 12 anos só podem usar a piscina acompanhadas de um adulto responsável. | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.597 | 0.597 (1) | 3.71s | OK |  |
| H3#2 | armadilha | Com quantos dias de antecedência preciso avisar a portaria sobre uma … | regulamento_condominio.pdf p.5 | Precisa avisar a portaria com 48 horas de antecedência. | regulamento_condominio.pdf p.5 | sim | sim | nenhum | sim | 0.547 | 0.547 (1) | 2.50s | OK |  |
| H4#2 | negacao | Preciso receber uma advertência antes de levar multa por pagar a taxa… | regulamento_condominio.pdf p.6 | Não, segundo o regulamento, a multa por atraso no pagamento da taxa condominial não depende de advertência prévia. | regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.786 | 0.786 (1) | 3.28s | OK |  |
| H5#2 | negacao | Posso levar meu cachorro para a academia do condomínio? | regulamento_condominio.pdf p.4 | Não, é proibida a permanência de animais na academia. | regulamento_condominio.pdf p.4 | sim | sim | nenhum | sim | 0.635 | 0.635 (1) | 2.21s | OK |  |
| H6#2 | conta | Qual é o valor de cada parcela da reforma da piscina? | ata_assembleia_2026.pdf p.2 | O valor de cada parcela da reforma da piscina é R$ 7.000,00, pois o orçamento total de R$ 42.000,00 será pago em 6 parcelas mensais. | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.767 | 0.767 (1) | 3.99s | OK |  |
| H7#2 | conta | Quantas unidades não estavam presentes na assembleia de 2026? | ata_assembleia_2026.pdf p.1 | 17 unidades não estavam presentes na assembleia de 2026. | ata_assembleia_2026.pdf p.1 | sim | sim | nenhum | sim | 0.624 | 0.624 (1) | 2.56s | OK |  |
| H8#2 | armadilha | Posso fazer uma obra barulhenta no sábado às 14h? | regulamento_condominio.pdf p.2 | Não, obras barulhentas são permitidas aos sábados apenas das 9h às 13h, conforme o Art. 5º. As 14h estão fora do horário autorizado. | regulamento_condominio.pdf p.2 | sim | sim | nenhum | sim | 0.643 | 0.643 (1) | 3.31s | OK |  |
| H9#2 | sem_resposta_plausivel | Qual é o valor da taxa de mudança cobrada pelo condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.650 | — | 3.58s | OK |  |
| H10#2 | sem_resposta | Quem é o zelador do condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.510 | — | 3.06s | OK |  |
| H11#2 | sem_resposta_plausivel | Quantos animais de estimação cada apartamento pode ter? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.729 | — | 3.03s | OK |  |
| H12#2 | sem_resposta_plausivel | Qual era o valor da taxa condominial em 2024? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.648 | — | 4.19s | OK |  |
| H13#2 | conta_combina_arquivos | Se eu danificar de propósito a quadra em junho de 2026, qual é o valo… | regulamento_condominio.pdf p.6, ata_assembleia_2026.pdf p.1 | A multa por danos intencionais à quadra em junho de 2026 corresponde a 3 taxas condominiais mensais vigentes. Conforme a ata da assembleia … | ata_assembleia_2026.pdf p.1, regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.521 | 0.521 (1) | 12.75s | OK |  |
| H14#2 | direta | Quem representa o Bloco B no conselho fiscal? | ata_assembleia_2026.pdf p.2 | Renata Lima representa o Bloco B no conselho fiscal. | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.504 | 0.504 (1) | 3.11s | OK |  |
| H15#2 | negacao | A síndica atual pode cumprir três mandatos seguidos? | regulamento_condominio.pdf p.1 | Não, a síndica atual não pode cumprir três mandatos seguidos. O mandato da síndica é de 2 anos, com permitida uma reeleição, o que totaliza… | regulamento_condominio.pdf p.1 | sim | sim | nenhum | sim | 0.429 | 0.429 (1) | 4.30s | OK |  |
| H16#2 | combina_trechos | Até que horas posso fazer uma festa no salão numa terça-feira, e qual… | regulamento_condominio.pdf p.3 | No salão de festas, os eventos podem terminar até 1h da manhã. Após as 22h, o som deve ser mantido em volume baixo, conforme exceção ao hor… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.710 | 0.710 (1) | 5.76s | OK |  |
| H1#3 | armadilha | Posso usar a churrasqueira até meia-noite numa sexta-feira? | regulamento_condominio.pdf p.3 | Sim, a churrasqueira pode ser usada até 22h, conforme estabelecido no Art. 10 do Capítulo III. Não consta nos documentos que o horário poss… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.595 | 0.595 (1) | 5.21s | OK |  |
| H2#3 | armadilha | Uma criança de 11 anos pode usar a piscina sozinha? | regulamento_condominio.pdf p.3 | Não, crianças menores de 12 anos só podem usar a piscina acompanhadas de um adulto responsável. | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.597 | 0.597 (1) | 3.65s | OK |  |
| H3#3 | armadilha | Com quantos dias de antecedência preciso avisar a portaria sobre uma … | regulamento_condominio.pdf p.5 | Precisa avisar a portaria com 48 horas de antecedência. | regulamento_condominio.pdf p.5 | sim | sim | nenhum | sim | 0.547 | 0.547 (1) | 2.47s | OK |  |
| H4#3 | negacao | Preciso receber uma advertência antes de levar multa por pagar a taxa… | regulamento_condominio.pdf p.6 | Não, segundo o regulamento, a multa por atraso no pagamento da taxa condominial não depende de advertência prévia. | regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.786 | 0.786 (1) | 3.26s | OK |  |
| H5#3 | negacao | Posso levar meu cachorro para a academia do condomínio? | regulamento_condominio.pdf p.4 | Não, é proibida a permanência de animais na academia. | regulamento_condominio.pdf p.4 | sim | sim | nenhum | sim | 0.635 | 0.635 (1) | 2.22s | OK |  |
| H6#3 | conta | Qual é o valor de cada parcela da reforma da piscina? | ata_assembleia_2026.pdf p.2 | O valor de cada parcela da reforma da piscina é R$ 7.000,00, pois o orçamento total de R$ 42.000,00 será pago em 6 parcelas mensais. | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.767 | 0.767 (1) | 4.01s | OK |  |
| H7#3 | conta | Quantas unidades não estavam presentes na assembleia de 2026? | ata_assembleia_2026.pdf p.1 | 17 unidades não estavam presentes na assembleia de 2026. | ata_assembleia_2026.pdf p.1 | sim | sim | nenhum | sim | 0.624 | 0.624 (1) | 2.53s | OK |  |
| H8#3 | armadilha | Posso fazer uma obra barulhenta no sábado às 14h? | regulamento_condominio.pdf p.2 | Não, obras barulhentas são permitidas aos sábados apenas das 9h às 13h, conforme o Art. 5º. As 14h estão fora do horário autorizado. | regulamento_condominio.pdf p.2 | sim | sim | nenhum | sim | 0.643 | 0.643 (1) | 3.30s | OK |  |
| H9#3 | sem_resposta_plausivel | Qual é o valor da taxa de mudança cobrada pelo condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.650 | — | 3.57s | OK |  |
| H10#3 | sem_resposta | Quem é o zelador do condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.510 | — | 3.04s | OK |  |
| H11#3 | sem_resposta_plausivel | Quantos animais de estimação cada apartamento pode ter? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.729 | — | 3.02s | OK |  |
| H12#3 | sem_resposta_plausivel | Qual era o valor da taxa condominial em 2024? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.648 | — | 4.19s | OK |  |
| H13#3 | conta_combina_arquivos | Se eu danificar de propósito a quadra em junho de 2026, qual é o valo… | regulamento_condominio.pdf p.6, ata_assembleia_2026.pdf p.1 | A multa por danos intencionais à quadra em junho de 2026 corresponde a 3 taxas condominiais mensais vigentes. Conforme a ata da assembleia … | ata_assembleia_2026.pdf p.1, regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.521 | 0.521 (1) | 12.77s | OK |  |
| H14#3 | direta | Quem representa o Bloco B no conselho fiscal? | ata_assembleia_2026.pdf p.2 | Renata Lima representa o Bloco B no conselho fiscal. | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.504 | 0.504 (1) | 3.12s | OK |  |
| H15#3 | negacao | A síndica atual pode cumprir três mandatos seguidos? | regulamento_condominio.pdf p.1 | Não, a síndica atual não pode cumprir três mandatos seguidos. O mandato da síndica é de 2 anos, com permitida uma reeleição, o que totaliza… | regulamento_condominio.pdf p.1 | sim | sim | nenhum | sim | 0.429 | 0.429 (1) | 4.29s | OK |  |
| H16#3 | combina_trechos | Até que horas posso fazer uma festa no salão numa terça-feira, e qual… | regulamento_condominio.pdf p.3 | No salão de festas, os eventos podem terminar até 1h da manhã. Após as 22h, o som deve ser mantido em volume baixo, conforme exceção ao hor… | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.710 | 0.710 (1) | 5.77s | OK |  |

## Variação entre repetições

Perguntas cujo resultado, recusa ou páginas citadas mudaram entre as rodadas: nenhuma.

## Conferência manual (obrigatória pelo PLANO)

Para cada linha respondida, abrir o PDF na página citada, conferir se o texto sustenta a resposta e escrever OK ou FALHA (com o motivo) na última coluna. As métricas automáticas não substituem esta etapa.
