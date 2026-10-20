# -*- coding: utf-8 -*-
"""
Checagens de integridade do projeto PBIP, rodadas antes de publicar (camada 1).

Publicar sem erro não significa que funciona: schemas 1.0.0 são aceitos no import
e o relatório abre em branco. Este script confere o que falha em silêncio — e as
exigências mínimas do enunciado de 20/10.

    python3 validar.py
"""
import json, os, re, sys, glob

os.chdir(os.path.dirname(os.path.abspath(__file__)))
ERR = []
def check(cond, msg):
    if not cond: ERR.append(msg)

MODEL = "PainelAviacao.SemanticModel/definition"
REPORT = "PainelAviacao.Report"
CSV = "dados/companhia_aerea_10mil_voos.csv"

# ── 0. o CSV que o modelo lê é o tratado, e bate com a consulta Fonte ───────
expr = open(os.path.join(MODEL, "expressions.tmdl"), encoding="utf-8").read()
cab = open(CSV, encoding="utf-8-sig").readline().strip().split(";")
ncols = int(re.search(r"Columns = (\d+)", expr).group(1))
check(ncols == len(cab), "Fonte declara %d colunas, o CSV tem %d" % (ncols, len(cab)))
tipadas = re.findall(r'\{"([^"]+)", (?:type \w+|Int64\.Type)\}', expr)
check(tipadas == cab, "colunas tipadas na Fonte divergem do cabeçalho do CSV")
check(os.path.basename(CSV) in re.search(r'pCaminhoCSV = "([^"]+)"', expr).group(1),
      "pCaminhoCSV não aponta para o CSV tratado")
check("/bruto/" not in expr, "o modelo não pode ler o CSV bruto")
with open(CSV, encoding="utf-8") as fh:
    linhas = [l.rstrip("\n").split(";") for l in fh][1:]
i_sit, i_atr = cab.index("Situacao_Voo"), cab.index("Atraso_Min")
check(all(l[i_atr] == "" for l in linhas if l[i_sit] == "Cancelado"),
      "CSV com atraso preenchido em voo cancelado — rode tratar_dados.py")

# ── 1. modelo: tabelas, colunas e medidas declaradas ────────────────────────
tables, measures, sortby = {}, set(), []
for path in glob.glob(os.path.join(MODEL, "tables", "*.tmdl")):
    txt = open(path, encoding="utf-8").read()
    tname = re.search(r"^table (\S+)", txt, re.M).group(1)
    cols = {m.group(1).strip("'") for m in re.finditer(r"^\tcolumn ('[^']+'|\S+)", txt, re.M)}
    tables[tname] = cols
    measures |= {m.group(1).strip("'") for m in re.finditer(r"^\tmeasure ('[^']+'|\S+)", txt, re.M)}
    sortby += [(tname, m.group(1).strip("'")) for m in re.finditer(r"sortByColumn: ('[^']+'|\S+)", txt)]
    # anotação órfã derruba o import inteiro, sem dizer onde
    n_ann = txt.count("annotation SummarizationSetBy")
    check(n_ann == len(cols), "%s: %d colunas para %d anotações SummarizationSetBy" % (tname, len(cols), n_ann))
    check("variation" not in txt, "%s: variation exige showAsVariationsOnly — remova" % tname)
for t, c in sortby:
    check(c in tables[t], "%s: sortByColumn aponta para coluna inexistente %s" % (t, c))

# referências dentro das fórmulas DAX: Tabela[coluna] e [Medida]
#   (erro de digitação aqui importa sem aviso e o visual sai vazio)
for path in glob.glob(os.path.join(MODEL, "tables", "*.tmdl")):
    txt = open(path, encoding="utf-8").read()
    dax = re.sub(r"\tpartition .*", "", txt, flags=re.S)          # M fica de fora
    dax = re.sub(r'"[^"\n]*"', '""', dax)                          # literais de texto também
    dax = re.sub(r"sourceColumn: .*", "", dax)                     # [Date] da tabela calculada
    for t, c in re.findall(r"\b(\w+)\[([^\]]+)\]", dax):
        check(c in tables.get(t, ()), "%s: DAX referencia coluna inexistente %s[%s]" % (os.path.basename(path), t, c))
    for m in re.findall(r"(?<![\w\]])\[([^\]]+)\]", dax):
        check(m in measures, "%s: DAX referencia medida inexistente [%s]" % (os.path.basename(path), m))
print("modelo: %d tabelas, %d colunas, %d medidas"
      % (len(tables), sum(len(c) for c in tables.values()), len(measures)))

# ── 2. relacionamentos ──────────────────────────────────────────────────────
rel = open(os.path.join(MODEL, "relationships.tmdl"), encoding="utf-8").read()
check("///" not in rel, "relationship não aceita descrição (///) — o import falha")
nrel = 0
for m in re.finditer(r"(from|to)Column: (\w+)\.(\S+)", rel):
    t, c = m.group(2), m.group(3)
    check(c in tables.get(t, ()), "relacionamento referencia coluna inexistente: %s.%s" % (t, c))
    nrel += 1
print("relacionamentos: %d" % (nrel // 2))

model_txt = open(os.path.join(MODEL, "model.tmdl"), encoding="utf-8").read()
refs = set(re.findall(r"^ref table (\S+)", model_txt, re.M))
check(refs == set(tables), "ref table divergente dos arquivos: %s" % (refs ^ set(tables)))

# ── 3. sourceColumn usa o nome DEPOIS do rename (senão só o refresh falha) ──
for path in glob.glob(os.path.join(MODEL, "tables", "*.tmdl")):
    txt = open(path, encoding="utf-8").read()
    if "= m\n" not in txt: continue
    renamed = {}
    for bloco in re.findall(r"Table\.RenameColumns\((.*?)\)\s*,?\n", txt, re.S):
        renamed.update(re.findall(r'\{"([^"]+)","([^"]+)"\}', bloco))
    for old, new in renamed.items():
        if old == new: continue
        check(("sourceColumn: %s\n" % old) not in txt,
              "%s: sourceColumn usa o nome anterior ao rename (%s -> %s)" % (path, old, new))

# ── 4. schemas do PBIR nas versões que renderizam ───────────────────────────
esperado = {
    os.path.join(REPORT, "definition.pbir"): "report/definitionProperties/1.0.0",
    os.path.join(REPORT, "definition/version.json"): "report/definition/versionMetadata/1.0.0",
    os.path.join(REPORT, "definition/report.json"): "report/definition/report/3.3.0",
    os.path.join(REPORT, "definition/pages/pages.json"): "report/definition/pagesMetadata/1.1.0",
}
for path, frag in esperado.items():
    j = json.load(open(path, encoding="utf-8"))
    check(frag in j["$schema"], "%s: schema fora da versão esperada (%s)" % (path, j["$schema"]))
ver = json.load(open(os.path.join(REPORT, "definition/version.json"), encoding="utf-8"))
check(ver["version"] == "2.0.0", "version.json deve ser 2.0.0")
rep = json.load(open(os.path.join(REPORT, "definition/report.json"), encoding="utf-8"))
check(isinstance(rep["themeCollection"]["baseTheme"].get("reportVersionAtImport"), dict),
      "reportVersionAtImport deve ser objeto")
check(os.path.exists(os.path.join(REPORT, "StaticResources/SharedResources",
                                  rep["resourcePackages"][0]["items"][0]["path"])),
      "arquivo físico do baseTheme ausente")

# ── 5. páginas, visuais, campos e geometria ─────────────────────────────────
pages = json.load(open(os.path.join(REPORT, "definition/pages/pages.json"), encoding="utf-8"))
check(pages["activePageName"] in pages["pageOrder"], "activePageName fora do pageOrder")
GRAFICOS = {"lineChart", "clusteredBarChart", "barChart", "clusteredColumnChart", "columnChart",
            "hundredPercentStackedColumnChart", "scatterChart", "tableEx", "pivotTable", "donutChart"}
por_pagina, nvis = {}, 0
for pname in pages["pageOrder"]:
    pdir = os.path.join(REPORT, "definition/pages", pname)
    pj = json.load(open(os.path.join(pdir, "page.json"), encoding="utf-8"))
    check("page/2.1.0" in pj["$schema"], "%s: schema de página errado" % pname)
    PW, PH = pj["width"], pj["height"]
    vis = []
    for vpath in sorted(glob.glob(os.path.join(pdir, "visuals", "*", "visual.json"))):
        vj = json.load(open(vpath, encoding="utf-8"))
        vname, p, vt = vj["name"], vj["position"], vj["visual"]["visualType"]
        vis.append(vj); nvis += 1
        check("visualContainer/2.12.0" in vj["$schema"], "%s/%s: schema de visual errado" % (pname, vname))
        check(os.path.basename(os.path.dirname(vpath)) == vname, "%s: nome difere da pasta" % vname)
        check(p["x"] >= 0 and p["y"] >= 0 and p["width"] > 0 and p["height"] > 0,
              "%s/%s: posição/dimensão inválida" % (pname, vname))
        check(p["x"] + p["width"] <= PW and p["y"] + p["height"] <= PH,
              "%s/%s: extrapola a página" % (pname, vname))
        if vt == "slicer":
            check(p["height"] >= 50, "%s/%s: slicer com %dpx — dropdown sai cortado" % (pname, vname, p["height"]))

        blob = json.dumps(vj, ensure_ascii=False)
        for ent, prop in re.findall(r'"Entity":\s*"([^"]+)"\}\},\s*"Property":\s*"([^"]+)"', blob):
            if ent == "_Medidas":
                check(prop in measures, "%s/%s: medida inexistente [%s]" % (pname, vname, prop))
            else:
                check(prop in tables.get(ent, ()), "%s/%s: coluna inexistente %s[%s]" % (pname, vname, ent, prop))
        # medidas citadas dentro de filtros Top N (usam Source, não Entity)
        for prop in re.findall(r'"Source":\s*"m"\}\},\s*"Property":\s*"([^"]+)"', blob):
            check(prop in measures, "%s/%s: filtro Top N com medida inexistente [%s]" % (pname, vname, prop))

        if vt in GRAFICOS:
            t = vj["visual"]["visualContainerObjects"].get("title", [{}])[0]["properties"]
            check(t.get("show", {}).get("expr", {}).get("Literal", {}).get("Value") == "true",
                  "%s/%s (%s): sem título explicativo" % (pname, vname, vt))
            check("subTitle" in vj["visual"]["visualContainerObjects"],
                  "%s/%s (%s): sem subtítulo dizendo a pergunta" % (pname, vname, vt))

    # sobreposição na mesma camada z
    for i, a in enumerate(vis):
        for c in vis[i + 1:]:
            pa, pc = a["position"], c["position"]
            if pa["z"] != pc["z"]: continue
            ox = min(pa["x"] + pa["width"], pc["x"] + pc["width"]) - max(pa["x"], pc["x"])
            oy = min(pa["y"] + pa["height"], pc["y"] + pc["height"]) - max(pa["y"], pc["y"])
            check(ox <= 0 or oy <= 0, "%s: %s e %s se sobrepõem na camada z=%d" % (pname, a["name"], c["name"], pa["z"]))
    por_pagina[pname] = vis

def kpis(vis):
    return [v for v in vis if v["visual"]["visualType"] == "card"
            and not v["visual"]["query"]["queryState"]["Values"]["projections"][0]["field"]["Measure"]["Property"].startswith("Contexto")]
def tipo(vis, *t): return [v for v in vis if v["visual"]["visualType"] in t]
def slicers_de(vis, ent=None):
    return [v for v in tipo(vis, "slicer") if ent is None or
            v["visual"]["query"]["queryState"]["Values"]["projections"][0]["field"]["Column"]["Expression"]["SourceRef"]["Entity"] == ent]

# ── 6. exigências do enunciado ──────────────────────────────────────────────
p1, p2 = por_pagina.get("pagina1", []), por_pagina.get("pagina2", [])
check(len(pages["pageOrder"]) == 2, "o enunciado pede duas páginas")
check(len(kpis(p1)) >= 4, "Página 1: menos de 4 cartões de KPI (%d)" % len(kpis(p1)))
check(len(tipo(p1, *GRAFICOS)) >= 2, "Página 1: menos de 2 gráficos")
check(len(slicers_de(p1, "dCalendario")) >= 1, "Página 1: falta filtro de período")
check(len({v["visual"]["visualType"] for v in tipo(p2, *GRAFICOS)}) >= 4,
      "Página 2: menos de 4 tipos de visualização diferentes")
check(len(slicers_de(p2)) >= 2, "Página 2: menos de 2 filtros interativos")
txt_p1 = json.dumps(p1, ensure_ascii=False)
check("Visão Executiva" in txt_p1, "Página 1: título não identifica a visão executiva")
check("simulados" in txt_p1 and "simulados" in json.dumps(p2, ensure_ascii=False),
      "as duas páginas precisam identificar os dados como simulados")
print("relatório: %d páginas, %d visuais" % (len(pages["pageOrder"]), nvis))
for pn, vis in por_pagina.items():
    print("  %s: %d KPIs, %d gráficos (%s), %d filtros" % (
        pn, len(kpis(vis)), len(tipo(vis, *GRAFICOS)),
        ", ".join(sorted({v["visual"]["visualType"] for v in tipo(vis, *GRAFICOS)})), len(slicers_de(vis))))

# ── 7. todo JSON do projeto é parseável ─────────────────────────────────────
for path in glob.glob("**/*.json", recursive=True) + glob.glob("**/.platform", recursive=True) + \
            ["PainelAviacao.pbip", os.path.join(REPORT, "definition.pbir")]:
    try: json.load(open(path, encoding="utf-8"))
    except Exception as e: ERR.append("JSON inválido: %s — %s" % (path, e))

if ERR:
    print("\n%d PROBLEMA(S):" % len(ERR))
    for e in ERR: print("  ✗ " + e)
    sys.exit(1)
print("\n✓ todas as checagens passaram")
