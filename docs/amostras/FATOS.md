# Amostras de demonstração — gabarito de fatos

Os PDFs desta pasta são **fictícios**, escritos para o DocuMind e gerados por
[`gerar_amostras.py`](gerar_amostras.py). Podem aparecer no vídeo e nos testes sem
restrição de autorização. A data de criação é fixa, então regerar produz arquivos
idênticos byte a byte. Para recriá-los:

```powershell
.venv\Scripts\python docs\amostras\gerar_amostras.py
```

Páginas em base 1, conferidas com `pypdf` 6.19.0 em 27/09/2026. Este gabarito é a
base da matriz de perguntas da T07. **Se o gerador mudar, confira e atualize esta
tabela no mesmo turno.**

## `regulamento_condominio.pdf` (6 páginas)

Caracteres extraídos por página: 612, 502, 1.349, 454, 352, 991. A página 3 passa de
1.200 caracteres de propósito, para exercitar a divisão em mais de um trecho com
sobreposição. As páginas 3 e 6 têm distratores (outros valores em R$, horários e
multas) para que a busca precise diferenciar trechos parecidos.

| Página | Fatos verificáveis |
|---|---|
| 1 | 48 unidades em 3 blocos (A, B, C), 16 por bloco; síndica com mandato de 2 anos, uma reeleição; síndica atual Marta Figueiredo. |
| 2 | Silêncio 22h–7h de domingo a quinta; 23h–8h nas noites de sexta e sábado. Obras com ruído: seg–sex 8h–17h, sáb 9h–13h, proibidas domingos e feriados. Aviso de obra com 5 dias úteis. |
| 3 | Piscina ter–dom 8h–21h, fechada às segundas para limpeza; menores de 12 anos acompanhados. Salão de festas: reserva com 15 dias, taxa R$ 150,00, 60 pessoas, até 1h, exceção ao silêncio com som baixo após 22h. Churrasqueira: reserva com 7 dias, R$ 80,00, 20 pessoas, até 22h. Quadra 8h–22h, 1 h por unidade por dia. Academia 6h–22h. Brinquedoteca até 10 anos, 8h–20h. Taxa de limpeza R$ 90,00; danos cobrados pelo valor do conserto. |
| 4 | 1 vaga por unidade, proibido alugar a não moradores; visitantes até 30 min na carga e descarga; animais com coleira, só elevador de serviço, proibidos na piscina e academia. |
| 5 | Mudanças seg–sáb 8h–18h, aviso de 48 h; lixo orgânico até 20h; recicláveis em papel, plástico, metal e vidro. |
| 6 | 1ª infração: advertência escrita; reincidência: multa de 1 taxa condominial; nova reincidência em 12 meses: 2 taxas; danos intencionais: conserto + 3 taxas sem advertência; atraso da taxa (vence dia 10): multa de 2% + juros de 1% ao mês; notificação na portaria ou por e-mail; recurso à assembleia em 15 dias; multas vão para o fundo de reserva. |

## `ata_assembleia_2026.pdf` (2 páginas)

| Página | Fatos verificáveis |
|---|---|
| 1 | Assembleia em 14/03/2026, 19h30; 31 de 48 unidades presentes; taxa condominial de R$ 620,00 para R$ 680,00 a partir de maio/2026; contas de 2025 aprovadas por unanimidade. |
| 2 | Reforma da piscina: R$ 42.000,00 em 6 parcelas; piscina fechada de 1º a 30/06/2026; conselho fiscal: Paulo Andrade (A), Renata Lima (B), Jorge Tavares (C); encerramento às 21h10. |

## `aviso_com_pagina_em_branco.pdf` (3 páginas)

Página 2 **em branco** (0 caracteres), para testar "ignora páginas vazias com aviso".
Páginas 1 e 3: manutenção dos elevadores do Bloco B em 20/10/2026, 9h–15h; usar escadas
ou o elevador do Bloco A. A citação correta desses fatos deve apontar p. 1 e p. 3,
nunca p. 2.

## `digitalizado_sem_texto.pdf` (1 página)

Só retângulos desenhados, sem camada de texto: `extract_text()` retorna 0 caracteres.
Serve para testar a detecção de PDF digitalizado/sem texto.

**PDF corrompido ou não-PDF:** não há arquivo versionado; os testes da T02 devem criar
bytes inválidos em memória (ex.: `b"isto nao e um pdf"`).

## Sugestões para a matriz (T07)

**Diretas:** número de unidades (p. 1); horário de obras no sábado (p. 2); taxa da
churrasqueira (p. 3, com o salão como distrator); vagas por unidade (p. 4); prazo de
recurso (p. 6).

**Paráfrase:** "Até que horas posso reformar o apartamento num sábado?" = horário de obras
no sábado (p. 2).

**Acompanhamento:** "Qual o horário da piscina?" → "E às segundas?" (fechada para limpeza,
p. 3).

**Combinam os dois arquivos:**

- Multa na primeira reincidência após maio/2026 → 1 taxa = R$ 680,00 (regulamento p. 6 + ata p. 1).
- A piscina abre numa terça-feira de junho/2026? → não, fechada para reforma (regulamento p. 3 + ata p. 2).

**Sem resposta nos documentos:**

- Qual é o CNPJ do condomínio?
- Qual é o valor do IPTU das unidades?

**Casos que exigem atenção:** festa no salão até 1h numa quarta-feira é permitida (p. 3
abre exceção ao silêncio da p. 2); a mesma pergunta para a churrasqueira tem resposta
diferente (até 22h). "Multa" é ambígua entre reincidência, dano intencional e atraso;
a resposta esperada precisa dizer qual.
