# -*- coding: utf-8 -*-
"""
Publica, valida e exporta o painel no Microsoft Fabric pela REST API.

    python3 publicar.py <pasta-com-token.json> <etapa> [args]

Etapas, nesta ordem:
    workspaces                     lista os workspaces e suas capacidades
    criar-ws <nome> <capacityId>   cria o workspace
    modelo <wsId>                  cria (ou atualiza) o semantic model a partir do TMDL
    credencial <wsId> <modelId>    fonte Web anônima, sem gateway
    refresh <wsId> <modelId>       dispara e acompanha o refresh
    relatorio <wsId> <modelId>     cria (ou atualiza) o relatório a partir do PBIR
    dax <wsId> <modelId>           confere os números contra o README
    pdf <wsId> <reportId> <saida>  exporta o PDF (camada 2 da validação)
    pbix <wsId> <reportId> <saida> baixa o .pbix com DataModel embutido

O token.json vem do login por device code (cliente público do Azure CLI) e fica fora
do repositório. Nenhum segredo é gravado por este script.
"""
import base64, glob, json, os, sys, time, urllib.error, urllib.parse, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
FABRIC = "https://api.fabric.microsoft.com/v1"
PBI = "https://api.powerbi.com/v1.0/myorg"
CLIENT = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
NOME = "PainelAviacao"

AUTH = sys.argv[1]
_tok = {}

def token(recurso):
    """Troca o refresh token pelo access token do recurso pedido (Fabric ou Power BI)."""
    if recurso in _tok and _tok[recurso][1] > time.time() + 60:
        return _tok[recurso][0]
    t = json.load(open(os.path.join(AUTH, "token.json")))
    scope = {"fabric": "https://api.fabric.microsoft.com/.default",
             "pbi": "https://analysis.windows.net/powerbi/api/.default"}[recurso]
    body = urllib.parse.urlencode({"grant_type": "refresh_token", "client_id": CLIENT,
                                   "refresh_token": t["refresh_token"],
                                   "scope": scope + " offline_access"}).encode()
    r = json.load(urllib.request.urlopen(
        "https://login.microsoftonline.com/organizations/oauth2/v2.0/token", body))
    t["refresh_token"] = r.get("refresh_token", t["refresh_token"])
    p = os.path.join(AUTH, "token.json")
    open(p, "w").write(json.dumps(t)); os.chmod(p, 0o600)
    _tok[recurso] = (r["access_token"], time.time() + int(r["expires_in"]))
    return r["access_token"]

def chamar(metodo, url, corpo=None, *, bruto=False, silencioso=False):
    recurso = "fabric" if url.startswith(FABRIC) else "pbi"
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dados, method=metodo,
                                 headers={"Authorization": "Bearer " + token(recurso),
                                          "Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=300)
    except urllib.error.HTTPError as e:
        if silencioso: raise
        print("HTTP %d em %s %s\n%s" % (e.code, metodo, url, e.read().decode()[:2000]))
        sys.exit(1)
    conteudo = resp.read()
    if bruto: return resp, conteudo
    return resp, (json.loads(conteudo) if conteudo.strip() else None)

def longa(resp, corpo):
    """Operação longa do Fabric: 202 + x-ms-operation-id → acompanha até terminar."""
    if resp.status != 202: return corpo
    op = resp.headers["x-ms-operation-id"]
    while True:
        time.sleep(int(resp.headers.get("Retry-After", 3)))
        _, st = chamar("GET", "%s/operations/%s" % (FABRIC, op))
        if st["status"] in ("Succeeded", "Failed"): break
    if st["status"] == "Failed":
        print("operação falhou:", json.dumps(st, ensure_ascii=False)[:2000]); sys.exit(1)
    try:   # updateDefinition não devolve corpo: 400 OperationHasNoResult é o esperado
        return chamar("GET", "%s/operations/%s/result" % (FABRIC, op), silencioso=True)[1]
    except urllib.error.HTTPError:
        return st

def partes(raiz, ignorar=(".platform",)):
    out = []
    for p in sorted(glob.glob(os.path.join(raiz, "**", "*"), recursive=True)):
        if os.path.isdir(p) or os.path.basename(p) in ignorar: continue
        rel = os.path.relpath(p, raiz).replace(os.sep, "/")
        out.append({"path": rel, "payload": base64.b64encode(open(p, "rb").read()).decode(),
                    "payloadType": "InlineBase64"})
    return out

def item_existente(ws, tipo, nome):
    _, r = chamar("GET", "%s/workspaces/%s/%s" % (FABRIC, ws, tipo))
    return next((i["id"] for i in r["value"] if i["displayName"] == nome), None)

etapa, args = sys.argv[2], sys.argv[3:]

if etapa == "workspaces":
    _, r = chamar("GET", FABRIC + "/workspaces")
    for w in r["value"]:
        print("%s | %s | capacity=%s" % (w["id"], w["displayName"], w.get("capacityId")))

elif etapa == "criar-ws":
    _, r = chamar("POST", FABRIC + "/workspaces", {"displayName": args[0], "capacityId": args[1]})
    print(r["id"])

elif etapa == "modelo":
    ws = args[0]
    defn = {"parts": partes(os.path.join(AQUI, NOME + ".SemanticModel"))}
    mid = item_existente(ws, "semanticModels", NOME)
    if mid:
        resp, c = chamar("POST", "%s/workspaces/%s/semanticModels/%s/updateDefinition" % (FABRIC, ws, mid),
                         {"definition": defn})
        longa(resp, c)
    else:
        resp, c = chamar("POST", "%s/workspaces/%s/semanticModels" % (FABRIC, ws),
                         {"displayName": NOME, "definition": defn})
        longa(resp, c)
        mid = item_existente(ws, "semanticModels", NOME)
    print(mid)

elif etapa == "credencial":
    ws, mid = args
    _, r = chamar("GET", "%s/groups/%s/datasets/%s/datasources" % (PBI, ws, mid))
    for ds in r["value"]:
        print("fonte:", ds["datasourceType"], ds.get("connectionDetails"))
        chamar("PATCH", "%s/gateways/%s/datasources/%s" % (PBI, ds["gatewayId"], ds["datasourceId"]),
               {"credentialDetails": {"credentialType": "Anonymous",
                                      "credentials": json.dumps({"credentialData": ""}),
                                      "encryptedConnection": "Encrypted", "encryptionAlgorithm": "None",
                                      "privacyLevel": "Public"}})
    print("credencial anônima aplicada em %d fonte(s)" % len(r["value"]))

elif etapa == "refresh":
    ws, mid = args
    chamar("POST", "%s/groups/%s/datasets/%s/refreshes" % (PBI, ws, mid), {"notifyOption": "NoNotification"})
    while True:
        time.sleep(10)
        _, r = chamar("GET", "%s/groups/%s/datasets/%s/refreshes?$top=1" % (PBI, ws, mid))
        st = r["value"][0]
        if st["status"] != "Unknown": break
    print(st["status"], st.get("serviceExceptionJson", ""))
    sys.exit(0 if st["status"] == "Completed" else 1)

elif etapa == "relatorio":
    ws, mid = args
    _, ws_info = chamar("GET", "%s/workspaces/%s" % (FABRIC, ws))
    defn = partes(os.path.join(AQUI, NOME + ".Report"))
    # o definition.pbir publicado NÃO é o local: schema 2.0.0 e byConnection (ver roteiro)
    pbir = {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {"byConnection": {"connectionString":
                'Data Source="powerbi://api.powerbi.com/v1.0/myorg/%s";initial catalog=%s;'
                'integrated security=ClaimsToken;semanticmodelid=%s' % (ws_info["displayName"], NOME, mid)}}}
    for p in defn:
        if p["path"] == "definition.pbir":
            p["payload"] = base64.b64encode(json.dumps(pbir, ensure_ascii=False).encode()).decode()
    rid = item_existente(ws, "reports", NOME)
    if rid:
        resp, c = chamar("POST", "%s/workspaces/%s/reports/%s/updateDefinition" % (FABRIC, ws, rid),
                         {"definition": {"parts": defn}})
        longa(resp, c)
    else:
        resp, c = chamar("POST", "%s/workspaces/%s/reports" % (FABRIC, ws),
                         {"displayName": NOME, "definition": {"parts": defn}})
        longa(resp, c)
        rid = item_existente(ws, "reports", NOME)
    print(rid)

elif etapa == "dax":
    ws, mid = args
    medidas = ["Voos Programados", "Voos Realizados", "Passageiros", "Receita", "Resultado", "Margem",
               "% Atrasados", "% Cancelados", "Atraso Médio (min)", "Taxa de Ocupação",
               "Custo dos Cancelamentos", "Satisfação Média", "Movimentos", "Ocorrências",
               "Contexto Resultado", "Contexto Cancelados", "Cor Resultado"]
    q = "EVALUATE ROW(%s)" % ", ".join('"%s", [%s]' % (m, m) for m in medidas)
    q2 = ('EVALUATE TOPN(10, FILTER(ADDCOLUMNS(VALUES(dRota[Rota]), "a", [Atraso Médio (rotas 20+ voos)]), '
          'NOT ISBLANK([a])), [a], DESC)')
    q3 = 'EVALUATE SUMMARIZECOLUMNS(dCalendario[Ano], "voos", [Voos Programados])'
    q4 = 'EVALUATE TOPN(3, ADDCOLUMNS(VALUES(dAeroporto[Aeroporto]), "mov", [Movimentos]), [mov], DESC)'
    for qq in (q, q2, q3, q4):
        _, r = chamar("POST", "%s/groups/%s/datasets/%s/executeQueries" % (PBI, ws, mid),
                      {"queries": [{"query": qq}], "serializerSettings": {"includeNulls": True}})
        for row in r["results"][0]["tables"][0]["rows"]:
            print(json.dumps(row, ensure_ascii=False))
        print("--")

elif etapa == "pdf":
    ws, rid, saida = args
    _, r = chamar("POST", "%s/groups/%s/reports/%s/ExportTo" % (PBI, ws, rid), {"format": "PDF",
           # sem o locale, o PDF sai em en-US (R$ 537.6M, 9,618) mesmo com o modelo em pt-BR
           "powerBIReportConfiguration": {"settings": {"locale": "pt-BR"}}})
    eid = r["id"]
    while True:
        time.sleep(5)
        _, st = chamar("GET", "%s/groups/%s/reports/%s/exports/%s" % (PBI, ws, rid, eid))
        print("  export %s %s%%" % (st["status"], st.get("percentComplete")))
        if st["status"] in ("Succeeded", "Failed"): break
    if st["status"] != "Succeeded": sys.exit(1)
    _, b = chamar("GET", "%s/groups/%s/reports/%s/exports/%s/file" % (PBI, ws, rid, eid), bruto=True)
    open(saida, "wb").write(b); print(saida, len(b), "bytes")

elif etapa == "pbix":
    ws, rid, saida = args
    _, b = chamar("GET", "%s/groups/%s/reports/%s/Export" % (PBI, ws, rid), bruto=True)
    open(saida, "wb").write(b); print(saida, len(b), "bytes")

else:
    print(__doc__); sys.exit(1)
