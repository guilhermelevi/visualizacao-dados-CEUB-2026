# -*- coding: utf-8 -*-
"""
Gera PainelAviacao.Report: as duas páginas do enunciado de 20/10.

  Página 1 · Visão Executiva — "O que está acontecendo na companhia?"  (diretoria)
  Página 2 · Visão Analítica — "Onde estão os problemas e o que os explica?"  (gestores)

    python3 build_report.py

Reescreve definition/pages/ por completo. Os nomes dos visuais vêm de um contador
determinístico, então rodar de novo produz exatamente os mesmos arquivos.

Os textos de insight são afirmações sobre o período completo e foram recalculados
contra o CSV tratado (ver MAPA-DAS-PERGUNTAS.md, seção Insights).
"""
import os, sys, json, shutil, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pbir import *

AQUI = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(AQUI, "PainelAviacao.Report")
X0, W = 24, 1232

def cols(n, x0=X0, width=W, gap=8):
    w = (width - gap * (n - 1)) // n
    return [(x0 + i * (w + gap), w) for i in range(n)]

CAL_MES = ("dCalendario", "Mes Ano", "Competência")

# ═════════════════════ PÁGINA 1 — VISÃO EXECUTIVA ═════════════════════
def pagina1():
    v = [header(80, "Visão Executiva — Desempenho da Companhia Aérea",
                "Diretoria  •  O que está acontecendo na companhia?  •  Dados simulados · jan/2025 a set/2026"),
         slicer((880, 13, 3, 180, 54), "dCalendario", "Ano", "Ano"),
         slicer((1068, 13, 4, 188, 54), "dCalendario", "Mes", "Mês")]

    # KPIs em ordem de importância: resultado → receita → operação → problemas
    kpis = [("Resultado", "Resultado (lucro ou prejuízo)", dict(color_measure="Cor Resultado", units=1000000, precision=1), "Contexto Resultado"),
            ("Receita", "Receita total", dict(units=1000000, precision=1), "Contexto Receita"),
            ("Voos Realizados", "Voos realizados", dict(), "Contexto Voos"),
            ("Passageiros", "Passageiros transportados", dict(), "Contexto Passageiros"),
            ("% Atrasados", "Voos atrasados", dict(color=WARN_TXT, precision=1), "Contexto Atrasos"),
            ("% Cancelados", "Voos cancelados", dict(color=BAD, precision=1), "Contexto Cancelados")]
    for (x, w), (mea, tit, kw, ctx) in zip(cols(6), kpis):
        v.append(moldura((x, 92, 5, w, 104)))
        v.append(card((x + 2, 94, 6, w - 4, 70), mea, tit, fontsize=22, framed=False, **kw))
        v.append(card_text((x + 2, 164, 7, w - 4, 28), ctx))

    v.append(linha((X0, 208, 8, 740, 318), CAL_MES,
                   [("Receita",), ("Resultado",)],
                   "Receita e resultado mês a mês",
                   "Pergunta 6 · a receita sobe em jan, jul e dez (alta temporada) e o resultado acompanha",
                   colors=[("Receita", INST), ("Resultado", OK)],
                   sort_column=("dCalendario", "Mes Ano"), axis_units=1000000))

    v.append(barras((772, 208, 9, 484, 318), CAL_MES, ("Voos Programados", "Voos"),
                    "Pontualidade mês a mês",
                    "Pergunta 5 · parte dos voos pontual, atrasada e cancelada em cada mês",
                    vtype="hundredPercentStackedColumnChart",
                    series=("dSituacao", "Situacao", "Situação"), series_colors=cores_situacao(),
                    labels=False, value_axis=True))
    v[-1]["visual"]["query"]["sortDefinition"] = sort_by_column("dCalendario", "Mes Ano")

    v.append(textbox(vid("txt"), (X0, 538, 10, 860, 160), [
        par([run("Insight executivo", size="11pt", bold=True),
             run("   período completo, sem filtros", size="8pt", color=MUTED, italic=True)]),
        spacer("4pt"),
        par([run("A companhia é lucrativa — ", size="9.5pt", color=MUTED),
             run("R$ 537,6 mi de resultado e margem de 72,8%", size="9.5pt", color=OK, bold=True),
             run(" —, mas ", size="9.5pt", color=MUTED),
             run("1 em cada 3 voos sai fora do horário", size="9.5pt", color=WARN_TXT, bold=True),
             run(" (30,6% atrasados + 3,8% cancelados). O risco está no cliente: a satisfação cai de "
                 "4,30 no voo pontual para 2,71 no atrasado e 1,67 no cancelado, e os cancelamentos "
                 "custaram R$ 4,5 mi sem gerar receita.", size="9.5pt", color=MUTED)]),
        spacer("4pt"),
        par([run("Decisão sugerida  ", size="9.5pt", color=INST, bold=True),
             run("tornar a pontualidade meta da diretoria (atrasos abaixo de 20%) e investir parte da "
                 "margem nos hubs de São Paulo e Rio, onde os atrasos se concentram — ver Visão Analítica.",
                 size="9.5pt", color=INST)])],
        bg=CARD, border=True, pad=(18, 18, 12, 10)))

    v.append(barras((892, 538, 11, 364, 160), ("dSituacao", "Situacao", "Situação"),
                    ("Satisfação Média", "Satisfação"),
                    "Satisfação por situação do voo", "nota média de 1 a 5 — o atraso custa a fidelidade",
                    series_colors=[cor_categoria("dSituacao", "Situacao", k, c) for k, c in COR_SITUACAO.items()]))
    v[-1]["visual"]["objects"]["labels"][0]["properties"]["labelPrecision"] = d(2)
    return page(R, "pagina1", "1 · Visão Executiva", v)

# ═════════════════════ PÁGINA 2 — VISÃO ANALÍTICA ═════════════════════
def pagina2():
    v = [header(80, "Visão Analítica — Onde estão os problemas",
                "Gestores e analistas  •  clique numa barra, ponto ou linha para filtrar a página  •  Dados simulados"),
         slicer((664, 13, 3, 150, 54), "dCalendario", "Ano", "Ano"),
         slicer((822, 13, 4, 210, 54), "dAeroporto", "Aeroporto", "Aeroporto de origem"),
         slicer((1040, 13, 5, 216, 54), "dSituacao", "Situacao", "Situação do voo")]

    kpis = [("Voos Programados", "Voos programados", dict()),
            ("% Atrasados", "Voos atrasados", dict(color=WARN_TXT, precision=1)),
            ("Atraso Médio (min)", "Atraso médio (min)", dict(color=WARN_TXT, precision=1)),
            ("Taxa de Ocupação", "Taxa de ocupação", dict(precision=1)),
            ("Margem", "Margem", dict(color_measure="Cor Resultado", precision=1))]
    for (x, w), (mea, tit, kw) in zip(cols(5, width=782), kpis):
        v.append(card((x, 88, 6, w, 62), mea, tit, fontsize=17, **kw))

    v.append(textbox(vid("txt"), (814, 88, 6, 442, 62), [
        par([run("Insight  ", size="8.5pt", bold=True),
             run("GRU, CGH e GIG atrasam 40% das partidas (28 min em média), contra 23% nos outros 11 "
                 "aeroportos — inclusive BSB, também hub. As 10 rotas mais atrasadas saem desses três.",
                 size="8pt", color=MUTED)]),
        par([run("Decisão  ", size="8.5pt", color=INST, bold=True),
             run("revisar slots e tempo de solo nesses três aeroportos.", size="8pt", color=INST)])],
        bg=CARD, border=True, pad=(12, 10, 6, 4)))

    # linha A — o que atrasa, por quê, e onde
    (xa, wa), (xb, wb), (xc, wc) = (X0, 404), (436, 404), (848, 408)
    v.append(barras((xa, 158, 7, wa, 270), ("dRota", "Rota", "Rota"),
                    ("Atraso Médio (rotas 20+ voos)", "Atraso médio (min)"),
                    "Rotas com maior atraso médio",
                    "Pergunta 1 · top 10 entre rotas com 20+ voos · minutos por voo realizado",
                    color=WARN, sort_measure="Atraso Médio (rotas 20+ voos)",
                    filters=topn("dRota", "Rota", "Atraso Médio (rotas 20+ voos)", 10)))
    v[-1]["visual"]["objects"]["labels"][0]["properties"]["labelPrecision"] = d(1)

    v.append(barras((xb, 158, 8, wb, 270), ("dMotivo", "Motivo", "Motivo"), ("Ocorrências", "Voos"),
                    "Principais motivos de atraso e cancelamento",
                    "Pergunta 3 · operação, manutenção e tripulação (controláveis) somam 52%",
                    vtype="barChart", series=("dSituacao", "Situacao", "Situação"),
                    series_colors=cores_situacao(), sort_measure="Ocorrências"))

    v.append(barras((xc, 158, 9, wc, 270), ("dAeroporto", "Aeroporto", "Aeroporto"), ("Movimentos", "Voos"),
                    "Aeroportos que concentram mais voos",
                    "Pergunta 2 · partidas + chegadas, por situação do voo",
                    vtype="barChart", series=("dSituacao", "Situacao", "Situação"),
                    series_colors=cores_situacao(), sort_measure="Movimentos", labels=False))

    # linha B — fatores e detalhamento
    v.append(dispersao((xa, 436, 10, wa, 268), ("dRota", "Rota", "Rota"),
                       ("Taxa de Ocupação", "Ocupação"), ("Margem", "Margem"),
                       "Ocupação × margem por rota",
                       "Pergunta 4 · cada ponto é uma rota: avião mais cheio, margem maior",
                       x_title="Taxa de ocupação", y_title="Margem"))

    v.append(linha((xb, 436, 11, wb, 268), CAL_MES,
                   [("% Atrasados", "Atrasados"), ("% Cancelados", "Cancelados")],
                   "Como os atrasos variam no tempo",
                   "Pergunta 6 · de nov a fev estão os piores meses de pontualidade",
                   colors=[("% Atrasados", WARN), ("% Cancelados", BAD)],
                   sort_column=("dCalendario", "Mes Ano")))

    v.append(tabela((xc, 436, 12, wc, 268),
                    [fcol("dRota", "Rota", "Rota"),
                     fmea("Voos Programados", "Voos"),
                     fmea("Passageiros", "Passageiros"),
                     fmea("Receita", "Receita"),
                     fmea("Taxa de Ocupação", "Ocupação"),
                     fmea("Atraso Médio (min)", "Atraso (min)")],
                    "Rotas com maior receita e passageiros",
                    "Pergunta 5 · clique no cabeçalho para reordenar",
                    sort_measure="Receita"))
    return page(R, "pagina2", "2 · Visão Analítica", v)

# ═════════════════════ esqueleto do relatório ═════════════════════
def jdump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2); f.write("\n")

def esqueleto():
    base = "https://developer.microsoft.com/json-schemas/fabric/"
    jdump(os.path.join(R, "definition.pbir"),
          {"$schema": base + "item/report/definitionProperties/1.0.0/schema.json", "version": "4.0",
           "datasetReference": {"byPath": {"path": "../PainelAviacao.SemanticModel"}}})
    jdump(os.path.join(R, "definition", "version.json"),
          {"$schema": base + "item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    jdump(os.path.join(R, "definition", "report.json"), {
        "$schema": base + "item/report/definition/report/3.3.0/schema.json",
        "themeCollection": {"baseTheme": {"name": "Fluent2-CY26SU09",
                                          "reportVersionAtImport": {"visual": "2.12.0", "report": "3.4.0", "page": "2.3.1"},
                                          "type": "SharedResources"}},
        "objects": {"section": [{"properties": {"verticalAlignment": s("Top")}}]},
        "resourcePackages": [{"name": "SharedResources", "type": "SharedResources",
                              "items": [{"name": "Fluent2-CY26SU09", "path": "BaseThemes/Fluent2-CY26SU09.json",
                                         "type": "BaseTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized",
                     "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True,
                     "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True}})
    jdump(os.path.join(R, ".platform"), {
        "$schema": base + "gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": "PainelAviacao"},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid5(uuid.NAMESPACE_URL, "painel-aviacao/report"))}})
    jdump(os.path.join(AQUI, "PainelAviacao.pbip"),
          {"version": "1.0", "artifacts": [{"report": {"path": "PainelAviacao.Report"}}],
           "settings": {"enableAutoRecovery": True}})

if __name__ == "__main__":
    esqueleto()
    shutil.rmtree(os.path.join(R, "definition", "pages"), ignore_errors=True)
    n = pagina1() + pagina2()
    pages_json(R, ["pagina1", "pagina2"], "pagina1")
    print("relatório: 2 páginas, %d visuais" % n)
