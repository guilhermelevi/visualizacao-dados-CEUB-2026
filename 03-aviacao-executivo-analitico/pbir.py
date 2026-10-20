# -*- coding: utf-8 -*-
"""Construtor dos visuais PBIR do painel executivo/analítico da companhia aérea."""
import json, os, hashlib

SCHEMA_VIS  = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json"
SCHEMA_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
SCHEMA_PGS  = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"

# paleta funcional — cor com significado, nunca decoração
INST, OK, WARN, BAD = "#123A5E", "#2E9B6B", "#E8A33D", "#C8414F"
WARN_TXT = "#B7791F"   # âmbar escurecido: o #E8A33D não tem contraste para texto em fundo branco
MUTED, BG, OUT, CARD, BORDER = "#63768A", "#F4F6F9", "#DFE5EC", "#FFFFFF", "#E2E8EF"
AXIS_TITLE = "#9AA9B8"
FONT = "Segoe UI, wf_segoe-ui_normal, helvetica, arial, sans-serif"

# a mesma situação tem a mesma cor em todos os visuais das duas páginas
COR_SITUACAO = {"Pontual": OK, "Atrasado": WARN, "Cancelado": BAD}

def lit(v):      return {"expr": {"Literal": {"Value": v}}}
def s(v):        return lit("'%s'" % v)
def d(v):        return lit("%sD" % v)
def b(v):        return lit("true" if v else "false")
def solid(hexc): return {"solid": {"color": {"expr": {"Literal": {"Value": "'%s'" % hexc}}}}}
def props(**kw): return [{"properties": dict(kw)}]

def solid_medida(prop, entity="_Medidas"):
    """Cor vinda de uma medida que devolve o hex — formatação condicional por valor de campo."""
    return {"solid": {"color": {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}},
                                                     "Property": prop}}}}}

_seq = [0]
def vid(prefix="v"):
    _seq[0] += 1
    h = hashlib.md5(("aviacao%d" % _seq[0]).encode()).hexdigest()[:13]
    return "%s%s" % (prefix, h)

# ---------- campos ----------
def _rotulo(proj, alias):
    """O nativeQueryRef não muda o rótulo exibido: só displayName renomeia eixo, legenda e coluna."""
    if alias: proj["displayName"] = alias
    return proj

def fcol(entity, prop, alias=None):
    return _rotulo({"field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
                    "queryRef": "%s.%s" % (entity, prop), "nativeQueryRef": alias or prop}, alias)

def fmea(prop, alias=None, entity="_Medidas"):
    return _rotulo({"field": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
                    "queryRef": "%s.%s" % (entity, prop), "nativeQueryRef": alias or prop}, alias)

def sort_by_measure(prop, direction="Descending", entity="_Medidas"):
    return {"sort": [{"field": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}},
            "Property": prop}}, "direction": direction}], "isDefaultSort": True}

def sort_by_column(entity, prop, direction="Ascending"):
    return {"sort": [{"field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}},
            "Property": prop}}, "direction": direction}], "isDefaultSort": True}

def topn(entity, prop, measure, n):
    """Filtro de visual Top N por medida — dinâmico, responde aos segmentadores."""
    col = lambda src: {"Column": {"Expression": {"SourceRef": {"Source": src}}, "Property": prop}}
    return {"filters": [{
        "name": hashlib.md5(("topn%s%s" % (prop, measure)).encode()).hexdigest()[:20],
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "type": "TopN",
        "filter": {"Version": 2,
                   "From": [{"Name": "subquery", "Type": 2, "Expression": {"Subquery": {"Query": {
                                "Version": 2,
                                "From": [{"Name": "d", "Entity": entity, "Type": 0},
                                         {"Name": "m", "Entity": "_Medidas", "Type": 0}],
                                "Select": [dict(col("d"), Name="field")],
                                "OrderBy": [{"Direction": 2, "Expression": {"Measure": {
                                    "Expression": {"SourceRef": {"Source": "m"}}, "Property": measure}}}],
                                "Top": n}}}},
                            {"Name": "d", "Entity": entity, "Type": 0}],
                   "Where": [{"Condition": {"In": {"Expressions": [col("d")],
                                                   "Table": {"SourceRef": {"Source": "subquery"}}}}}]}}]}

# ---------- moldura padrão ----------
def frame(title=None, subtitle=None, bg=CARD, border=True, pad=(10, 10, 6, 6), header=False):
    o = {}
    if bg:
        o["background"] = props(show=b(True), color=solid(bg), transparency=d(0))
    else:
        o["background"] = props(show=b(False))
    o["visualHeader"] = props(show=b(header))
    o["border"] = props(show=b(True), color=solid(BORDER), radius=d(8), width=d(1)) if border \
                  else props(show=b(False))
    if title:
        o["title"] = props(show=b(True), text=s(title), fontSize=d(11), fontColor=solid(INST),
                           bold=b(True), alignment=s("left"), titleWrap=b(False))
    else:
        o["title"] = props(show=b(False))
    if subtitle:
        o["subTitle"] = props(show=b(True), text=s(subtitle), fontSize=d("8.5"),
                              fontColor=solid(MUTED), alignment=s("left"), titleWrap=b(False))
    l, r, t, bo = pad
    o["padding"] = props(left=d(l), right=d(r), top=d(t), bottom=d(bo))
    return o

def visual(name, pos, vtype, query=None, objects=None, vco=None, filters=None):
    v = {"visualType": vtype, "drillFilterOtherVisuals": True}
    if query: v["query"] = query
    if objects: v["objects"] = objects
    if vco: v["visualContainerObjects"] = vco
    out = {"$schema": SCHEMA_VIS, "name": name,
           "position": {"x": pos[0], "y": pos[1], "z": pos[2], "width": pos[3], "height": pos[4]},
           "visual": v}
    if filters: out["filterConfig"] = filters
    return out

def qs(**roles):
    return {"queryState": {k: {"projections": v} for k, v in roles.items() if v}}

def eixo(show=True, titulo=None, grid=False, size=8.5):
    p = dict(show=b(show), fontSize=d(size), labelColor=solid(MUTED), showAxisTitle=b(bool(titulo)),
             gridlineShow=b(grid), gridlineColor=solid(BORDER))
    if titulo:
        p.update(titleText=s(titulo), titleFontSize=d("8.5"), titleColor=solid(AXIS_TITLE))
    return props(**p)

def legenda(show=True, pos="Top"):
    return props(show=b(show), position=s(pos), fontSize=d(9), labelColor=solid(MUTED), showTitle=b(False))

def cor_categoria(entity, prop, valor, hexc):
    """Fixa a cor de UMA categoria/série por igualdade de valor."""
    return {"properties": {"fill": solid(hexc)},
            "selector": {"data": [{"scopeId": {"Comparison": {
                "ComparisonKind": 0,
                "Left": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
                "Right": {"Literal": {"Value": "'%s'" % valor}}}}}]}}

def cores_situacao():
    return [cor_categoria("dSituacao", "Situacao", k, v) for k, v in COR_SITUACAO.items()]

# ---------- cartões ----------
def card(pos, measure, title, *, color=INST, color_measure=None, fontsize=22, units=0, precision=None,
         framed=True):
    lab = dict(color=solid_medida(color_measure) if color_measure else solid(color),
               fontSize=d(fontsize), bold=b(True), labelDisplayUnits=d(units))
    if precision is not None: lab["labelPrecision"] = d(precision)
    o = {"labels": props(**lab), "categoryLabels": props(show=b(False)), "wordWrap": props(show=b(False))}
    vco = frame(pad=(4, 4, 4, 0)) if framed else frame(bg=None, border=False, pad=(4, 4, 6, 0))
    vco["title"] = props(show=b(True), text=s(title), fontSize=d(9), fontColor=solid(MUTED),
                         alignment=s("center"), titleWrap=b(True))
    return visual(vid(), pos, "card", qs(Values=[fmea(measure)]), o, vco)

def card_text(pos, measure, *, color=MUTED, fontsize=9):
    """Cartão que exibe uma medida de texto — o contexto embaixo do número."""
    o = {"labels": props(color=solid(color), fontSize=d(fontsize), bold=b(False)),
         "categoryLabels": props(show=b(False)),
         "wordWrap": props(show=b(True))}
    return visual(vid(), pos, "card", qs(Values=[fmea(measure)]), o,
                  frame(bg=None, border=False, pad=(6, 6, 0, 2)))

def slicer(pos, entity, prop, header_text, *, single=False):
    o = {"data": props(mode=s("Dropdown")),
         "header": props(show=b(True), fontColor=solid(INST), fontSize=d("8.5"),
                         text=s(header_text), background=solid(CARD), outline=s("None")),
         "items": props(fontColor=solid(INST), fontSize=d("8.5"), background=solid(CARD)),
         "selection": props(selectAllCheckboxEnabled=b(True), singleSelect=b(single))}
    return visual(vid(), pos, "slicer", qs(Values=[fcol(entity, prop, header_text)]), o, frame())

# ---------- texto ----------
def textbox(name, pos, paragraphs, *, bg=None, border=False, pad=(24, 24, 15, 10)):
    vco = {"visualHeader": props(show=b(False)), "title": props(show=b(False))}
    if bg: vco["background"] = props(show=b(True), color=solid(bg), transparency=d(0))
    vco["border"] = props(show=b(True), color=solid(BORDER), radius=d(8), width=d(1)) if border \
                    else props(show=b(False))
    l, r, t, bo = pad
    vco["padding"] = props(left=d(l), top=d(t), right=d(r), bottom=d(bo))
    return {"$schema": SCHEMA_VIS, "name": name,
            "position": {"x": pos[0], "y": pos[1], "z": pos[2], "width": pos[3], "height": pos[4]},
            "visual": {"visualType": "textbox",
                       "objects": {"general": props(paragraphs=paragraphs)},
                       "visualContainerObjects": vco, "drillFilterOtherVisuals": True}}

def par(runs, align="left"):
    return {"horizontalTextAlignment": align, "textRuns": runs}

def run(text, *, size="9pt", color=INST, bold=False, italic=False):
    st = {"fontSize": size, "color": color, "fontFamily": FONT}
    if bold: st["fontWeight"] = "bold"
    if italic: st["fontStyle"] = "italic"
    return {"value": text, "textStyle": st}

def spacer(size="4pt"):
    return par([run("", size=size, color="#FFFFFF")])

def header(height, title, subtitle, *, width=1280):
    return textbox(vid("txt"), (0, 0, 0, width, height),
                   [par([run(title, size="16pt", color="#FFFFFF", bold=True)]),
                    par([run(subtitle, size="9pt", color="#BFD0E0")])], bg=INST)

def moldura(pos):
    """Fundo com borda que agrupa cartão + linha de contexto num bloco só."""
    return textbox(vid("txt"), pos, [par([run("", size="4pt", color=CARD)])],
                   bg=CARD, border=True, pad=(0, 0, 0, 0))

# ---------- gráficos ----------
def barras(pos, category, measure, title, subtitle, *, vtype="clusteredBarChart", series=None,
           color=INST, series_colors=None, sort_measure=None, labels=True, label_units=0,
           value_axis=False, filters=None, legend=None):
    """Barras e colunas: agrupada, empilhada ou 100%. category/measure: tuplas (…, alias)."""
    q = qs(Category=[fcol(*category)], Series=[fcol(*series)] if series else None, Y=[fmea(*measure)])
    if sort_measure: q["sortDefinition"] = sort_by_measure(sort_measure)
    o = {"categoryAxis": eixo(size=8.5),
         "valueAxis": eixo(show=value_axis, grid=value_axis),
         "labels": props(show=b(labels), fontSize=d("8.5"), color=solid(MUTED),
                         labelDisplayUnits=d(label_units)),
         "legend": legenda(show=bool(series) if legend is None else legend)}
    o["dataPoint"] = series_colors if series_colors else props(fill=solid(color))
    return visual(vid(), pos, vtype, q, o, frame(title, subtitle), filters)

def linha(pos, category, values, title, subtitle, *, colors=None, sort_column=None, axis_units=0,
          continuo=False):
    q = qs(Category=[fcol(*category)], Y=[fmea(*v) for v in values])
    if sort_column: q["sortDefinition"] = sort_by_column(*sort_column)
    va = eixo(grid=True)
    va[0]["properties"]["labelDisplayUnits"] = d(axis_units)
    o = {"legend": legenda(show=len(values) > 1),
         "categoryAxis": eixo(size=8),
         "valueAxis": va,
         "labels": props(show=b(False)),
         "lineStyles": props(strokeWidth=d(2.5))}
    if continuo:   # eixo categórico com muitos meses ganha barra de rolagem em visual estreito
        o["categoryAxis"][0]["properties"]["axisType"] = s("Scalar")
    if colors:
        o["dataPoint"] = [{"properties": {"fill": solid(c)}, "selector": {"metadata": "_Medidas.%s" % m}}
                          for m, c in colors]
    return visual(vid(), pos, "lineChart", q, o, frame(title, subtitle))

def dispersao(pos, category, x, y, title, subtitle, *, color=INST, x_title=None, y_title=None):
    q = qs(Category=[fcol(*category)], X=[fmea(*x)], Y=[fmea(*y)])
    o = {"dataPoint": props(fill=solid(color)),
         "categoryAxis": eixo(titulo=x_title, grid=True),
         "valueAxis": eixo(titulo=y_title, grid=True),
         "legend": legenda(show=False),
         "bubbles": props(bubbleSize=d(-20)),
         "fillPoint": props(show=b(True))}
    return visual(vid(), pos, "scatterChart", q, o, frame(title, subtitle))

def tabela(pos, values, title, subtitle, *, sort_measure=None):
    q = qs(Values=values)
    if sort_measure: q["sortDefinition"] = sort_by_measure(sort_measure)
    o = {"grid": props(gridVertical=b(False), gridHorizontal=b(True), gridHorizontalColor=solid(BORDER),
                       rowPadding=d(2), outlineColor=solid(BORDER)),
         "columnHeaders": props(fontColor=solid("#FFFFFF"), backColor=solid(INST), fontSize=d(8),
                                bold=b(True), alignment=s("Center"), wordWrap=b(True)),
         "values": props(fontColor=solid(INST), fontSize=d(8),
                         backColorPrimary=solid(CARD), backColorSecondary=solid("#F8FAFC")),
         "total": props(totals=b(True), fontColor=solid(INST), backColor=solid(BG), bold=b(True))}
    return visual(vid(), pos, "tableEx", q, o, frame(title, subtitle))

# ---------- escrita ----------
def page(root, name, display, visuals, *, bg=BG, out=OUT):
    pdir = os.path.join(root, "definition", "pages", name)
    os.makedirs(os.path.join(pdir, "visuals"), exist_ok=True)
    pj = {"$schema": SCHEMA_PAGE, "name": name, "displayName": display,
          "displayOption": "FitToPage", "height": 720, "width": 1280,
          "objects": {"background": props(color=solid(bg), transparency=d(0)),
                      "outspace": props(color=solid(out), transparency=d(0))}}
    with open(os.path.join(pdir, "page.json"), "w", encoding="utf-8") as f:
        json.dump(pj, f, ensure_ascii=False, indent=2); f.write("\n")
    for v in visuals:
        vdir = os.path.join(pdir, "visuals", v["name"])
        os.makedirs(vdir, exist_ok=True)
        with open(os.path.join(vdir, "visual.json"), "w", encoding="utf-8") as f:
            json.dump(v, f, ensure_ascii=False, indent=2); f.write("\n")
    return len(visuals)

def pages_json(root, order, active):
    p = os.path.join(root, "definition", "pages", "pages.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"$schema": SCHEMA_PGS, "pageOrder": order, "activePageName": active},
                  f, ensure_ascii=False, indent=2); f.write("\n")
