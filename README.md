# Visualização de Dados — CEUB, 5º semestre

Projetos Power BI em formato **PBIP/PBIR**, versionáveis e publicáveis no Microsoft Fabric
pela REST API. Prof. José Antonio de Paiva Júnior · Turma A.

| Exercício | O que é | Escala |
|---|---|---|
| [01 · Hospitalar](01-hospitalar/) | Os cinco tipos de **visualização especializada** da aula 05: cartões/KPIs, treemap, mapa, matriz e tabela | 100 mil atendimentos · 6 páginas · 75 visuais · 49 medidas |
| [02 · Companhia Aérea](02-companhia-aerea/) | Dashboard executivo respondendo as 15 perguntas do enunciado | 6.200 voos · 5 páginas · 62 objetos · 44 medidas |
| [03 · Aviação: Executivo e Analítico](03-aviacao-executivo-analitico/) | Duas páginas para dois públicos — Visão Executiva (diretoria) e Visão Analítica (gestores) — com os erros do CSV corrigidos antes de modelar | 10.000 voos · 2 páginas · 41 visuais · 31 medidas |

Cada pasta tem seu `README.md` (como publicar e republicar) e um `MAPA-DAS-PERGUNTAS.md`
com a justificativa de cada escolha de visual.

## Os dados são lidos daqui mesmo

Os modelos leem o CSV por HTTP deste repositório, com credencial anônima — sem gateway,
sem OneDrive, e a atualização agendada funciona sem configuração extra. Dois parâmetros
controlam isso em cada modelo:

| Parâmetro | Valor |
|---|---|
| `pUrlBase` | `https://raw.githubusercontent.com` |
| `pCaminhoCSV` | `guilhermelevi/visualizacao-dados-CEUB-2026/main/<exercício>/dados/<arquivo>.csv` |

> Se o repositório voltar a ser privado, os refreshes quebram. A URL raw precisa de acesso anônimo.

## [Roteiro para gerar um painel do zero](ROTEIRO-GERAR-PAINEL.md)

O pipeline completo — do enunciado ao painel publicado e validado — com as armadilhas de
formato do PBIR que fazem um relatório abrir em branco sem dar erro.
