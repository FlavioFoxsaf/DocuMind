# Índice dos relatórios de avaliação

Todos de 27/09/2026. Os relatórios são registros: não são apagados quando a configuração
muda. Use esta tabela para saber quais descrevem o sistema atual.

## Vigentes (configuração atual: Ollama local, `qwen3:14b` + `qwen3-embedding:0.6b`, raciocínio ligado)

| Arquivo | O que mede | Resultado |
|---|---|---|
| `20260927-1924-real-ollama-qwen314b-c1000-o150-k4.md` | matriz principal, 16 perguntas × 3 | **48/48** |
| `20260927-1925-real-ollama-qwen314b-c500-o100-k4.md` | matriz principal com trechos de 500/100 | **16/16** |
| `20260927-1918-real-ollama-qwen314b-matriz_dificil-c1000-o150-k4.md` | matriz difícil, 16 perguntas × 3 | **48/48** |
| `20260927-1927-injecao-qwen314b.md` | 3 ataques de injeção pelo PDF × 3 | **9/9** (nunca adotou o ataque; cita o PDF malicioso como fonte divergente no J1) |

## Comparações que justificam as decisões (T13)

| Arquivo | Configuração | Resultado | Decisão que apoia |
|---|---|---|---|
| `20260927-1915-real-ollama-qwen38b-matriz_dificil-c1000-o150-k4.md` | 8b com raciocínio (amostragem recomendada) | 45/48 (H13 errada 3/3) | 14b como padrão; 8b fica como opção mais rápida |
| `20260927-1919-real-ollama-qwen38b-sem-raciocinio-matriz_dificil-c1000-o150-k4.md` | 8b sem raciocínio | 35/48 | raciocínio ligado |

## Históricos (não descrevem mais o sistema)

| Arquivo | Por que é histórico |
|---|---|
| `20260927-1908-real-ollama-qwen38b-matriz_dificil-c1000-o150-k4.md` | 8b com `temperature 0` (gulosa com raciocínio, abandonada) e critérios antigos de H4/H15, corrigidos depois |
| `20260927-1827-real-ollama-c1000-o150-k4.md`, `20260927-1828-real-ollama-c500-o100-k4.md` | 8b com `temperature 0` (T12), antes da troca para 14b e da amostragem recomendada |
| `20260927-1643-*`, `1644-*`, `1648-*`, `1722-*` (`real-c1000-o150-k4`) | API Gemini, **removida do projeto** na T13 |
| `20260927-0112-dry-run-*` | dry-run offline: não mede qualidade |

## Sensibilidade ao `top_k` (T13)

| Arquivo | Configuração | Resultado | Decisão que apoia |
|---|---|---|---|
| `20260927-1934-real-ollama-qwen314b-matriz-c1000-o150-k2.md` | 14b, `top_k 2`, matriz principal | 16/16 | — |
| `20260927-1935-real-ollama-qwen314b-matriz_dificil-c1000-o150-k2.md` | 14b, `top_k 2`, matriz difícil | 15/16 (H13: perde a ata com R$ 680) | manter `top_k = 4` |
