# Mapa das perguntas — Dashboard Executivo e Analítico

Cada pergunta do enunciado de 20/10/2026 → o visual que responde → por que esse visual.
Todos os números deste documento são do **período completo** (jan/2025 a set/2026, sem
filtros) e foram recalculados contra o CSV tratado. **Dados simulados.**

---

## Página 1 · Visão Executiva

**Público:** diretoria. **Pergunta-guia:** *o que está acontecendo na companhia aérea?*

| # | Pergunta | Visual | Resposta | Por que esse visual |
|---|---|---|---|---|
| 1 | Quantos voos foram realizados? | Cartão **Voos realizados** + contexto "de 10.000 programados" | 9.618 | Número único → cartão. O contexto separa realizados de programados |
| 2 | Quantos passageiros foram transportados? | Cartão **Passageiros transportados** + ocupação | 1.234.577 (ocupação 75,3%) | Idem; a ocupação diz se o número é bom |
| 3 | Qual foi a receita total? | Cartão **Receita total** + receita por passageiro | R$ 738,4 mi (R$ 598 por passageiro) | Idem |
| 4 | Qual foi o resultado (lucro ou prejuízo)? | Cartão **Resultado**, verde se lucro e vermelho se prejuízo, + margem | R$ 537,6 mi de lucro, margem de 72,8% | A cor vem de uma medida (`Cor Resultado`): o sinal do número decide a cor, não o designer |
| 5 | % de voos atrasados e cancelados | Cartões **Voos atrasados** (âmbar) e **Voos cancelados** (vermelho) + **coluna 100% empilhada** mês a mês | 30,6% atrasados · 3,8% cancelados | O cartão dá o número; a coluna 100% mostra a composição de cada mês sem o volume distorcer |
| 6 | Como evoluíram voos ou receita? | **Linhas** de receita e resultado por mês | Picos em jan, jul e dez (alta temporada); o resultado acompanha | Evolução no tempo → linha. As duas séries estão na mesma unidade (R$), então um eixo só |

**Requisitos atendidos:** 6 cartões de KPI (mínimo 4) · 3 gráficos (mínimo 2) · filtros de
período **Ano** e **Mês** · título "Visão Executiva" · KPIs da esquerda para a direita em
ordem de importância: resultado → receita → operação → problemas.

**Teste dos 10 segundos:** a primeira linha diz "lucrativa" (verde) e "1 em 3 fora do
horário" (âmbar e vermelho). O quadro de insight embaixo diz o que fazer.

---

## Página 2 · Visão Analítica

**Público:** gestores e analistas. **Pergunta-guia:** *onde estão os problemas e o que os explica?*

O enunciado pede 4 das 6 perguntas; a página responde às **6**.

| # | Pergunta | Visual | O que mostra | Por que esse visual |
|---|---|---|---|---|
| 1 | Rotas com maior atraso médio | **Barras horizontais**, top 10, âmbar | Todas saem de GRU, CGH ou GIG; a pior é GRU-FLN (32,7 min) | Ranking → barra ordenada. Rótulo de rota é longo → horizontal. Filtro Top N por medida: responde aos segmentadores |
| 2 | Aeroportos que concentram mais voos | **Barras empilhadas** por situação | GRU (4.289 movimentos), BSB e CGH somam 49% | Conta **partidas + chegadas** (relação inativa de destino). A pilha mostra volume e problema juntos: GRU é grande **e** atrasa |
| 3 | Principais motivos | **Barras empilhadas** atrasado/cancelado | Problema operacional (27%) e meteorologia (27%) lideram; 52% são controláveis | Comparar categorias → barra. A pilha separa o que atrasa do que cancela: meteorologia é o maior motivo de **cancelamento** |
| 4 | Ocupação × resultado financeiro | **Dispersão**, um ponto por rota | Sim: mais ocupação, mais margem (r = 0,72 nas rotas com 20+ voos) | Relação entre duas medidas → dispersão. O eixo Y é a **margem**, não o lucro: o lucro absoluto depende da distância (r ≈ 0 com a ocupação) e esconderia a relação |
| 5 | Rotas com maior receita e passageiros | **Tabela** ordenada por receita | GRU-BSB lidera (R$ 55,4 mi, 90.501 passageiros); top 10 rotas = 31% da receita | Várias métricas por rota com valor exato → tabela; clicar no cabeçalho reordena por passageiros |
| 6 | Como os atrasos variam entre períodos | **Linhas** % atrasados e % cancelados por mês | Nov a fev são os piores meses (nov/25: 40%) | Evolução → linha; mesma unidade (%) nas duas séries |

**Requisitos atendidos:** 5 tipos de visualização diferentes (mínimo 4) · 3 segmentadores
(**Ano**, **Aeroporto de origem**, **Situação do voo**) além do filtro cruzado por clique ·
comparação entre categorias em todas as barras · título + subtítulo com a pergunta em todo
visual · leitura em duas linhas: *o que e onde* (rotas, motivos, aeroportos) → *por que e
detalhe* (ocupação, tempo, tabela).

**Desafio do gestor (que rotas/aeroportos merecem atenção):** o cartão de insight no topo
responde direto, e o gráfico de aeroportos mostra a mesma coisa na pilha âmbar.

---

## Decisões de método

- **Ranking de atraso só com amostra.** 77 das 180 rotas têm menos de 20 voos; a menor tem 1.
  A medida `Atraso Médio (rotas 20+ voos)` fica vazia abaixo disso, para um único voo
  atrasado não liderar o ranking.
- **Percentuais sobre programados.** Pontuais + atrasados + cancelados = 100%, nas duas páginas.
- **Ocupação e margem ponderadas.** `Σ passageiros ÷ Σ assentos` e `Σ lucro ÷ Σ receita`,
  nunca a média dos percentuais de cada linha.
- **Erros do CSV corrigidos antes do modelo** — ver `QUALIDADE-DOS-DADOS.md`. Sem a correção,
  o atraso médio seria 20,2 min (e não 21,0) e a ocupação 72,4% (e não 75,3%).

## Cores

Uma regra: **cor é significado**. Verde = pontual/lucro, âmbar = atraso, vermelho =
cancelamento/prejuízo, azul-escuro = neutro. As mesmas três cores de situação aparecem
idênticas nas duas páginas (cartões, colunas, pilhas, satisfação, linha do tempo).
Categorias sem julgamento (rotas, aeroportos, motivos) não ganham matiz próprio. Texto em
âmbar usa um tom escurecido (`#B7791F`), porque o âmbar dos gráficos não tem contraste
suficiente para leitura.

---

## Insights (seção 6 do enunciado)

### Insight executivo

**A companhia é lucrativa, mas 1 em cada 3 voos sai fora do horário — e é isso que
ameaça o resultado.** Resultado de R$ 537,6 mi e margem de 72,8%; ao mesmo tempo, 30,6%
dos voos atrasam e 3,8% são cancelados. A satisfação cai de **4,30** no voo pontual para
**2,71** no atrasado e **1,67** no cancelado, e os cancelamentos custaram **R$ 4,5 mi**
sem gerar receita.

**Decisão:** tornar a pontualidade uma meta acompanhada pela diretoria (por exemplo,
atrasos abaixo de 20% dos voos) e destinar parte da margem a um plano de pontualidade nos
hubs de São Paulo e Rio.

### Insight analítico

**O problema de atraso tem endereço: GRU, CGH e GIG.** Esses três aeroportos atrasam
**40,1%** das partidas, com **28,0 min** de atraso médio, contra **22,9%** e **15,4 min**
nos outros 11 — inclusive Brasília, que também é hub e tem volume comparável. As 10 rotas
com maior atraso médio saem todas deles. E 52% das ocorrências têm causa controlável
(problema operacional, manutenção, tripulação).

**Decisão:** revisar slots e tempo de solo (turnaround) em GRU, CGH e GIG, começando pelas
rotas do top 10, e reforçar equipes de solo e manutenção nesses três aeroportos de novembro
a fevereiro, os meses com mais atraso.

---

## Reflexão final

| | Visão Executiva | Visão Analítica |
|---|---|---|
| Pergunta | O que está acontecendo? | Onde estão os problemas e por quê? |
| Leitor | Diretoria, 10 segundos | Gestor, tempo para investigar |
| Forma | Poucos números grandes, duas tendências, uma recomendação | Rankings, composição, relação entre variáveis, tabela |
| Filtros | Só período | Período, aeroporto, situação e clique cruzado |

A executiva mostra **o que** merece atenção (pontualidade); a analítica mostra **onde**
(três aeroportos, dez rotas, quatro meses do ano) e **por quê** (causas controláveis,
ocupação puxando a margem).
