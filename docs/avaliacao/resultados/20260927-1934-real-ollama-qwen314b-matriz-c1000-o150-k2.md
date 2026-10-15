# Avaliação DocuMind — real-ollama-qwen314b — 27/09/2026 19:34

## Configuração

- Documentos: regulamento_condominio.pdf, ata_assembleia_2026.pdf
- Trechos: 9 (chunk_size 1000, overlap 150)
- Tempo de indexação: 1.59s
- top_k: 2
- min_score usado: 0.0
- Repetições: 1
- Pausa entre perguntas: 0.0s
- Modelo de geração: qwen3:14b
- Raciocínio (think): ligado
- Modelo de embedding: qwen3-embedding:0.6b
- Perguntas: 16

## Métricas agregadas

| Métrica | Valor |
|---|---|
| Execuções (pergunta × repetição) | 16 (erros de API: 0) |
| Resultado OK (todos os critérios) | 16/16 (100%) |
| Acerto de recuperação (alguma evidência no top-2) | 14/14 (100%) |
| Recuperação completa (todas as evidências no top-2) | 13/14 (93%) |
| Citação correta (cita página esperada) | 14/14 (100%) |
| Termos-chave presentes | 14/14 (100%) |
| Recusa nas perguntas sem resposta | 2/2 (100%) |
| Falsa recusa nas respondíveis | 0/14 (0%) |
| Score top-1, respondíveis | n=14, mín 0.514, mediana 0.650, máx 0.814 |
| Score top-1, sem resposta | n=2, mín 0.529, mediana 0.568, máx 0.607 |

### Sugestão de `MIN_SCORE`

- Maior limiar que não recusa nenhuma respondível: **0.513**.
- Margem sobre a sem resposta de maior score: **-0.094**.
- Os scores NÃO separam as classes (a sem resposta mais alta, 0.607, passa a respondível mais baixa, 0.514). O score sozinho não decide a recusa; se usar MIN_SCORE, fique em no máximo 0.513, só como rede de segurança contra perguntas totalmente fora do assunto.

## Resultado por pergunta

Legenda: Rec. = evidência no top-k; Cit. = citou página esperada; Recusa ok = recusou se e só se devia; Pos. = posição da melhor evidência no ranking completo.

| ID | Tipo | Pergunta | Esperado (páginas) | Resposta observada | Páginas citadas | Rec. | Cit. | Termos faltando | Recusa ok | Top-1 | Evid. (pos.) | Tempo | Resultado | Conferência manual |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1#1 | direta | Quantas unidades residenciais tem o condomínio? | regulamento_condominio.pdf p.1 | O condomínio possui 48 unidades residenciais. | regulamento_condominio.pdf p.1 | sim | sim | nenhum | sim | 0.626 | 0.626 (1) | 7.18s | OK |  |
| D2#1 | direta | Qual é o horário permitido para obras com ruído aos sábados? | regulamento_condominio.pdf p.2 | Obras com ruído são permitidas aos sábados, das 9h às 13h. | regulamento_condominio.pdf p.2 | sim | sim | nenhum | sim | 0.814 | 0.814 (1) | 3.89s | OK |  |
| D3#1 | direta | Qual é a taxa de reserva da churrasqueira? | regulamento_condominio.pdf p.3 | A taxa de reserva da churrasqueira é de R$ 80,00. | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.648 | 0.648 (1) | 3.34s | OK |  |
| D4#1 | direta | Quantas vagas de garagem cada unidade tem? | regulamento_condominio.pdf p.4 | Cada unidade tem direito a 1 vaga de garagem. | regulamento_condominio.pdf p.4 | sim | sim | nenhum | sim | 0.652 | 0.652 (1) | 2.45s | OK |  |
| D5#1 | direta | Qual é o prazo para recorrer de uma multa? | regulamento_condominio.pdf p.6 | O prazo para recorrer de uma multa é de 15 dias contados do recebimento da notificação. | regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.605 | 0.605 (1) | 3.41s | OK |  |
| P1#1 | parafrase | Até que horas posso reformar o apartamento num sábado? | regulamento_condominio.pdf p.2 | Reformas com ruído são permitidas aos sábados das 9h às 13h. | regulamento_condominio.pdf p.2 | sim | sim | nenhum | sim | 0.514 | 0.514 (1) | 3.26s | OK |  |
| P2#1 | parafrase | Quanto custa reservar o espaço do churrasco? | regulamento_condominio.pdf p.3 | A taxa de reserva da churrasqueira é de R$ 80,00. | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.587 | 0.587 (1) | 3.16s | OK |  |
| C1#1 | combina_arquivos | Qual é o valor da multa na primeira reincidência cometida depois de m… | regulamento_condominio.pdf p.6, ata_assembleia_2026.pdf p.1 | O valor da multa na primeira reincidência cometida depois de maio de 2026 é equivalente a 1 (uma) taxa condominial mensal vigente, que, a p… | ata_assembleia_2026.pdf p.1, regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.603 | 0.603 (1) | 4.59s | OK |  |
| C2#1 | combina_arquivos | A piscina vai abrir numa terça-feira de junho de 2026? | ata_assembleia_2026.pdf p.2, regulamento_condominio.pdf p.3 | Não, a piscina não abrirá numa terça-feira de junho de 2026, pois está fechada de 1º a 30 de junho de 2026 para reforma. | ata_assembleia_2026.pdf p.2 | sim | sim | nenhum | sim | 0.703 | 0.703 (1) | 4.11s | OK |  |
| C3#1 | combina_trechos | Posso fazer uma festa no salão até 1h da manhã numa quarta-feira? | regulamento_condominio.pdf p.3, regulamento_condominio.pdf p.2 | Sim, é permitido fazer uma festa no salão de festas até 1h da manhã, desde que seja reservado com antecedência de 15 dias, pague a taxa de … | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.692 | 0.692 (1) | 6.62s | OK |  |
| F1#1 | acompanhamento_base | Qual o horário da piscina? | regulamento_condominio.pdf p.3 | A piscina funciona de terça-feira a domingo, das 8h às 21h. Às segundas-feiras a piscina permanece fechada para limpeza. | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.741 | 0.741 (1) | 8.89s | OK |  |
| F2#1 | acompanhamento | E às segundas? | regulamento_condominio.pdf p.3 | Às segundas-feiras a piscina permanece fechada para limpeza. | regulamento_condominio.pdf p.3 | sim | sim | nenhum | sim | 0.714 | 0.714 (1) | 2.44s | OK |  |
| S1#1 | sem_resposta | Qual é o CNPJ do condomínio? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.607 | — | 3.18s | OK |  |
| S2#1 | sem_resposta | Qual é o valor do IPTU das unidades? | recusa | (recusa: not_found) | — | — | — | — | sim | 0.529 | — | 3.16s | OK |  |
| A1#1 | ambigua | Qual é o valor da multa? | regulamento_condominio.pdf p.6 | O valor da multa depende da infração e da taxa condominial vigente. Para reincidência, é equivalente a 1 taxa mensal (R$ 680,00 a partir de… | ata_assembleia_2026.pdf p.1, regulamento_condominio.pdf p.6 | sim | sim | nenhum | sim | 0.586 | 0.586 (1) | 9.48s | OK |  |
| I1#1 | independente_apos_outra | Qual é o horário de silêncio nas noites de sexta-feira? | regulamento_condominio.pdf p.2 | O horário de silêncio nas noites de sexta-feira é das 23h às 8h. | regulamento_condominio.pdf p.2 | sim | sim | nenhum | sim | 0.687 | 0.616 (2) | 3.44s | OK |  |

## Efeito da pergunta anterior na busca

Cada célula mostra **com a anterior / sem a anterior**. A busca real concatena a pergunta anterior à atual. No acompanhamento isso deve ajudar; na pergunta independente, pode atrapalhar (contaminação).

| ID | Tipo | Anterior | Rec. | Posição da evidência | Score da evidência |
|---|---|---|---|---|---|
| F2#1 | acompanhamento | Qual o horário da piscina? | sim / sim | 1 / 2 | 0.714 / 0.391 |
| I1#1 | independente_apos_outra | Qual é a taxa de reserva da churrasqueira? | sim / sim | 2 / 1 | 0.616 / 0.735 |

## Conferência manual (obrigatória pelo PLANO)

Para cada linha respondida, abrir o PDF na página citada, conferir se o texto sustenta a resposta e escrever OK ou FALHA (com o motivo) na última coluna. As métricas automáticas não substituem esta etapa.
