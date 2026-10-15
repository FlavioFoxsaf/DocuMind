# DocuMind — desenvolvimento e estudo

Esta pasta preserva o código de desenvolvimento, o ambiente local, os testes e os
documentos de planejamento e avaliação. A preparação fica nas pastas irmãs
[Entrevista/](../Entrevista/README.md) e [video explicativo/](<../video explicativo/README.md>).

**A pasta preparada para o avaliador é [`../DocuMind_Entrega/`](../DocuMind_Entrega/).**
O arquivo para anexar é [`../DocuMind_Entrega.zip`](../DocuMind_Entrega.zip). A entrega
contém somente a aplicação Streamlit/Ollama, um README de execução, configuração e
dois PDFs fictícios. Não compacte esta pasta de desenvolvimento para enviar.

## Onde encontrar cada material

| Material | Local |
|---|---|
| Guia completo do ambiente e decisões técnicas | [docs/README_DESENVOLVIMENTO.md](docs/README_DESENVOLVIMENTO.md) |
| Estado atual, histórico e próxima ação | [docs/planejamento/STATUS.md](docs/planejamento/STATUS.md) |
| Plano geral | [docs/planejamento/PLANO.md](docs/planejamento/PLANO.md) |
| Histórico da migração local | [docs/planejamento/PLANO_MIGRACAO_LOCAL.md](docs/planejamento/PLANO_MIGRACAO_LOCAL.md) |
| Treinamento guiado ponta a ponta — começar aqui | [Entrevista/treinamento_ponta_a_ponta.md](../Entrevista/treinamento_ponta_a_ponta.md) |
| Defesa técnica e estudo | [Entrevista/defesa_tecnica.md](../Entrevista/defesa_tecnica.md) |
| Roteiro e checklist do vídeo | [video explicativo/roteiro_video.md](<../video explicativo/roteiro_video.md>) |
| Contratos dos módulos | [docs/contratos/](docs/contratos/) |
| Perguntas e scripts de avaliação | [docs/avaliacao/README.md](docs/avaliacao/README.md) |
| Índice dos resultados reais | [docs/avaliacao/resultados/INDICE.md](docs/avaliacao/resultados/INDICE.md) |
| PDFs fictícios e gabarito | [docs/amostras/FATOS.md](docs/amostras/FATOS.md) |
| Testes automatizados | `tests/` |

## Executar no ambiente de desenvolvimento já instalado

No PowerShell, a partir desta pasta:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Ollama e modelos devem estar disponíveis. Para instalar tudo em outro computador,
siga o [Readme.txt de entrega](../DocuMind_Entrega/Readme.txt).

## Referência para a próxima IA

Leia `docs/planejamento/PLANO.md`, `docs/planejamento/PLANO_MIGRACAO_LOCAL.md` e
`docs/planejamento/STATUS.md`. Os caminhos de código e os comandos nesses materiais
continuam relativos à raiz desta pasta de desenvolvimento.

A entrega é uma cópia da versão Streamlit atual; FastAPI não foi implementado.
Se o código mudar, atualize a cópia em `../DocuMind_Entrega/` e recrie o ZIP antes de
submeter. Ambientes virtuais, `.env`, caches, testes e materiais de estudo não entram
no ZIP. Uma `.venv` pode ser criada localmente na pasta de entrega para executá-la.
