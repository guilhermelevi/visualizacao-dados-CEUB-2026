# Painel Aviação — Dashboard Executivo e Analítico

Projeto Power BI (formato **PBIP/PBIR**) do exercício de 20/10/2026: um relatório com
**duas páginas para dois públicos**, sobre 10.000 voos simulados de jan/2025 a set/2026.

| Página | Público | Pergunta |
|---|---|---|
| 1 · Visão Executiva | Diretoria | O que está acontecendo na companhia? |
| 2 · Visão Analítica | Gestores e analistas | Onde estão os problemas e o que os explica? |

**No ar:** [abrir no Power BI](https://app.powerbi.com/groups/d9b5fe16-3b73-4005-ab61-315bfdb7500a/reports/8f25cd98-1424-4f77-a7e0-7959311ad97f)
· workspace **Aviacao CEUB**

Star schema com 6 dimensões, 31 medidas DAX e 41 visuais. A cobertura de cada pergunta,
as justificativas e os dois insights estão em [MAPA-DAS-PERGUNTAS.md](MAPA-DAS-PERGUNTAS.md).

```
                 dCalendario (21 meses)
                        |
  dAeroporto (14) ==+   |   +-- dRota (180)
   origem (ativa)   |   |   |
   destino (inativa)+-- fVoos --+-- dAeronave (5)
                        |  10.000 voos · só chaves e métricas
         dSituacao (3) -+-- dMotivo (6)
```

```
dados/bruto/companhia_aerea_10mil_voos.csv   ← arquivo recebido, nunca editado
dados/companhia_aerea_10mil_voos.csv         ← arquivo TRATADO, o único que o modelo lê
tratar_dados.py                              ← audita e corrige o bruto → gera o tratado
QUALIDADE-DOS-DADOS.md                       ← erros encontrados e corrigidos (gerado)
build_model.py                               ← gera PainelAviacao.SemanticModel (TMDL)
build_report.py + pbir.py                    ← geram PainelAviacao.Report (PBIR)
validar.py                                   ← checagens que rodam antes de publicar
publicar.py                                  ← publica, confere por DAX e exporta PDF e .pbix
PainelAviacao.pbip                           ← abre o projeto no Power BI Desktop
```

## Regenerar tudo

```bash
python3 tratar_dados.py    # bruto → tratado + QUALIDADE-DOS-DADOS.md (sai com erro se achar o que não sabe corrigir)
python3 build_model.py     # TMDL
python3 build_report.py    # PBIR
python3 validar.py         # camada 1
```

Os quatro são determinísticos: rodar de novo produz arquivos idênticos, então o `git diff`
mostra só o que mudou de verdade.

## Qualidade dos dados

O CSV recebido tinha **erros nos 382 voos cancelados**: atraso, duração real, ocupação,
preço e margem preenchidos com valor quando, para voo que não decolou, **não se aplicam**.
Zero entra na média como medição — o atraso médio sairia 20,2 min em vez de 21,0 e a
ocupação 72,4% em vez de 75,3%. `tratar_dados.py` deixa esses campos vazios e confere
outras 20 regras de integridade (todas sem violação). Detalhe em
[QUALIDADE-DOS-DADOS.md](QUALIDADE-DOS-DADOS.md).

## Fonte de dados

O CSV tratado é lido por HTTP, com credencial anônima, do repositório público do curso:

| Parâmetro | Valor |
|---|---|
| `pUrlBase` | `https://raw.githubusercontent.com` |
| `pCaminhoCSV` | `guilhermelevi/visualizacao-dados-CEUB-2026/main/03-aviacao-executivo-analitico/dados/companhia_aerea_10mil_voos.csv` |

> Se o repositório voltar a ser privado, o refresh quebra: a URL raw precisa de acesso anônimo.

O arquivo usa `;` como separador e **ponto** decimal — por isso a tipagem usa a cultura
`"en-US"` (o contrário do CSV hospitalar). Campos vazios viram `null`, que as médias ignoram.

## Status: publicado e validado

| Item | Link |
|---|---|
| Relatório | https://app.powerbi.com/groups/d9b5fe16-3b73-4005-ab61-315bfdb7500a/reports/8f25cd98-1424-4f77-a7e0-7959311ad97f |
| Semantic model | https://app.powerbi.com/groups/d9b5fe16-3b73-4005-ab61-315bfdb7500a/datasets/6355cf67-dec3-455f-aba6-fc834e8fdf18 |

Publicado em 20/10/2026 pela REST API. As três camadas passaram:

1. **Estrutural** — `validar.py`.
2. **Números** — a consulta DAX devolveu exatamente os valores da tabela abaixo, o top 10 de
   rotas e os movimentos por aeroporto calculados localmente.
3. **Renderização** — PDF exportado e lido visual a visual. A primeira leitura pegou 10
   defeitos que as camadas 1 e 2 não veem (números em en-US, "1M" no cartão, filtros e
   textos cortados, eixos com barra de rolagem, apelidos de campo ignorados, ordem
   alfabética na satisfação, rótulo ilegível); todos corrigidos e conferidos num segundo e
   terceiro PDF. O PDF final está em `../ENTREGA/PainelAviacao.pdf`.

## Republicar depois de editar

```bash
python3 build_model.py && python3 build_report.py && python3 validar.py
python3 publicar.py <pasta-do-token> modelo d9b5fe16-3b73-4005-ab61-315bfdb7500a
python3 publicar.py <pasta-do-token> refresh  d9b5fe16-3b73-4005-ab61-315bfdb7500a 6355cf67-dec3-455f-aba6-fc834e8fdf18
python3 publicar.py <pasta-do-token> relatorio d9b5fe16-3b73-4005-ab61-315bfdb7500a 6355cf67-dec3-455f-aba6-fc834e8fdf18
```

O token vem do login por device code (ver o `ROTEIRO-GERAR-PAINEL.md` da raiz do curso,
Etapa 5) e fica fora do repositório.

### Números que a consulta DAX tem que devolver

Sem filtros, período completo. Calculados direto do CSV tratado:

| Medida | Valor esperado |
|---|---|
| Voos Programados | 10.000 |
| Voos Realizados | 9.618 |
| Passageiros | 1.234.577 |
| Receita | R$ 738.407.679 |
| Resultado | R$ 537.630.450 |
| Margem | 72,8% |
| % Atrasados · % Cancelados | 30,6% · 3,8% |
| Atraso Médio (min) | 21,0 |
| Taxa de Ocupação | 75,3% |
| Custo dos Cancelamentos | R$ 4.488.213 |
| Satisfação Média | 3,71 |

Se o atraso médio vier **20,2** ou a ocupação **72,4%**, o modelo está lendo o CSV bruto.

## Entregar

`../ENTREGA/` tem o `PainelAviacao.pbix` (exportado do Service, com `DataModel` embutido —
abre em qualquer Power BI Desktop sem depender do Fabric), o PDF das duas páginas, o CSV
tratado e os documentos. O `.pbix` é um retrato: se o painel mudar, exporte de novo com
`publicar.py … pbix`.
