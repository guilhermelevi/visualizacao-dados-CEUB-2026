# -*- coding: utf-8 -*-
"""
Gera PainelAviacao.SemanticModel/definition em TMDL.

    python3 build_model.py

Star schema: fVoos guarda só chaves e métricas; todo atributo descritivo vive
numa dimensão. Os lineageTags são uuid5 do caminho do objeto, então rodar de
novo produz arquivos idênticos.
"""
import os, uuid, shutil

AQUI = os.path.dirname(os.path.abspath(__file__))
SM = os.path.join(AQUI, "PainelAviacao.SemanticModel")
DEF = os.path.join(SM, "definition")
NS = uuid.UUID("6f1c2a52-03a0-4c8e-9a1d-a0b1c2d3e4f5")

def tag(*path):
    return str(uuid.uuid5(NS, "/".join(path)))

def bloco(texto, nivel):
    """Indenta um texto multilinha em `nivel` tabs."""
    return "\n".join(("\t" * nivel + l) if l.strip() else "" for l in texto.strip("\n").split("\n"))

# ── colunas e medidas ───────────────────────────────────────────────────────
def coluna(tabela, nome, tipo, desc, *, src=None, expr=None, fmt=None, soma="none",
           ordem=None, chave=False, cat=None, inferido=False):
    q = "'%s'" % nome if any(c in nome for c in " -()") else nome
    L = ["\t/// %s" % desc]
    if expr is None:
        L.append("\tcolumn %s" % q)
    elif "\n" in expr:
        L.append("\tcolumn %s =" % q); L.append(bloco(expr, 3))
    else:
        L.append("\tcolumn %s = %s" % (q, expr))
    L.append("\t\tdataType: %s" % tipo)
    if chave: L.append("\t\tisKey")
    if fmt: L.append("\t\tformatString: %s" % fmt)
    L.append("\t\tlineageTag: %s" % tag(tabela, nome))
    if cat: L.append("\t\tdataCategory: %s" % cat)
    L.append("\t\tsummarizeBy: %s" % soma)
    if inferido: L.append("\t\tisNameInferred")
    if src: L.append("\t\tsourceColumn: %s" % src)
    if ordem: L.append("\t\tsortByColumn: %s" % ("'%s'" % ordem if " " in ordem else ordem))
    L += ["", "\t\tannotation SummarizationSetBy = Automatic", ""]
    return "\n".join(L)

def medida(nome, expr, desc, pasta, fmt=None):
    L = ["\t/// %s" % desc]
    if "\n" in expr:
        L.append("\tmeasure '%s' =" % nome); L.append(bloco(expr, 3))
    else:
        L.append("\tmeasure '%s' = %s" % (nome, expr))
    if fmt: L.append("\t\tformatString: %s" % fmt)
    L.append("\t\tdisplayFolder: %s" % pasta)
    L.append("\t\tlineageTag: %s" % tag("_Medidas", nome))
    L.append("")
    return "\n".join(L)

def particao_m(nome, grupo, m):
    return "\n".join(["\tpartition %s = m" % nome, "\t\tmode: import", "\t\tqueryGroup: %s" % grupo,
                      "\t\tsource =", bloco(m, 4), ""])

def tabela(nome, desc, corpo, *, extra_header=""):
    h = "/// %s\ntable %s\n\tlineageTag: %s\n" % (desc, nome, tag(nome))
    if extra_header: h += extra_header + "\n"
    return h + "\n" + corpo.rstrip("\n") + "\n\n\tannotation PBI_ResultType = Table\n"

MOEDA, INT, PCT, DEC1 = '"R$" #,0', "#,0", "0.0%", "#,0.0"

# ═════════════════════════════ fVoos ═════════════════════════════
RENOMES = [("ID_Voo", "id_voo"), ("Data_Voo", "data_voo"), ("Horario_Partida", "horario_partida"),
           ("Faixa_Horaria", "faixa_horaria"), ("Aeroporto_Origem", "origem_iata"),
           ("Aeroporto_Destino", "destino_iata"), ("Rota", "rota"), ("Tipo_Aeronave", "tipo_aeronave"),
           ("Situacao_Voo", "situacao_voo"), ("Motivo_Ocorrencia", "motivo"),
           ("Capacidade_Aeronave", "capacidade"), ("Passageiros", "passageiros"),
           ("Taxa_Ocupacao_Pct", "taxa_ocupacao"), ("Duracao_Prevista_Min", "duracao_prevista_min"),
           ("Duracao_Real_Min", "duracao_real_min"), ("Atraso_Min", "atraso_min"),
           ("Preco_Medio_Passagem_R$", "preco_medio"), ("Receita_R$", "receita"),
           ("Custo_Operacional_R$", "custo"), ("Lucro_R$", "lucro"), ("Satisfacao_1a5", "satisfacao")]

def fvoos():
    t = "fVoos"
    c = [
        coluna(t, "id_voo", "string", "Identificador único do voo (chave degenerada)", src="id_voo"),
        coluna(t, "data_voo", "dateTime", "Data do voo — chave para dCalendario", src="data_voo", fmt="Long Date"),
        coluna(t, "horario_partida", "string", "Horário programado de partida (HH:MM)", src="horario_partida"),
        coluna(t, "faixa_horaria", "string", "Manhã, tarde ou noite — derivada do horário de partida da própria linha",
               src="faixa_horaria", ordem="Ordem Faixa Horaria"),
        coluna(t, "origem_iata", "string", "Aeroporto de partida — chave para dAeroporto (relação ativa)", src="origem_iata"),
        coluna(t, "destino_iata", "string", "Aeroporto de chegada — chave para dAeroporto (relação inativa, usada em Movimentos)", src="destino_iata"),
        coluna(t, "rota", "string", "Par origem-destino — chave para dRota", src="rota"),
        coluna(t, "tipo_aeronave", "string", "Modelo da aeronave — chave para dAeronave", src="tipo_aeronave"),
        coluna(t, "situacao_voo", "string", "Pontual, Atrasado ou Cancelado — chave para dSituacao", src="situacao_voo"),
        coluna(t, "motivo", "string", "Causa do atraso ou cancelamento — chave para dMotivo", src="motivo"),
        coluna(t, "capacidade", "int64", "Assentos ofertados no voo", src="capacidade", fmt=INT, soma="sum"),
        coluna(t, "passageiros", "int64", "Passageiros transportados", src="passageiros", fmt=INT, soma="sum"),
        coluna(t, "taxa_ocupacao", "double", "Passageiros ÷ capacidade. Vazio em voo cancelado", src="taxa_ocupacao", fmt=PCT),
        coluna(t, "duracao_prevista_min", "int64", "Duração programada do voo em minutos", src="duracao_prevista_min", fmt=INT),
        coluna(t, "duracao_real_min", "int64", "Duração realizada em minutos. Vazio em voo cancelado", src="duracao_real_min", fmt=INT),
        coluna(t, "atraso_min", "int64", "Minutos de atraso na partida. Vazio em voo cancelado", src="atraso_min", fmt=INT),
        coluna(t, "preco_medio", "double", "Preço médio pago por passageiro. Vazio em voo cancelado", src="preco_medio", fmt=MOEDA),
        coluna(t, "receita", "double", "Receita bruta do voo", src="receita", fmt=MOEDA, soma="sum"),
        coluna(t, "custo", "double", "Custo operacional do voo (existe também no cancelado)", src="custo", fmt=MOEDA, soma="sum"),
        coluna(t, "lucro", "double", "Receita menos custo", src="lucro", fmt=MOEDA, soma="sum"),
        coluna(t, "satisfacao", "double", "Nota média de satisfação, de 1 a 5", src="satisfacao", fmt="0.0"),
        # vem do Power Query: ordem calculada em DAX a partir da própria coluna que ela
        # ordena gera dependência circular, e o refresh falha
        coluna(t, "Ordem Faixa Horaria", "int64", "Ordenação de manhã, tarde e noite",
               src="Ordem Faixa Horaria", fmt="0"),
        coluna(t, "Faixa de Ocupacao", "string", "Agrupa a ocupação da linha em faixas",
               expr='''
VAR o = fVoos[taxa_ocupacao]
RETURN
    SWITCH( TRUE(),
        ISBLANK( o ), "Cancelado",
        o < 0.6,  "Abaixo de 60%",
        o < 0.75, "60% a 75%",
        o < 0.9,  "75% a 90%",
        "90% ou mais"
    )''', ordem="Ordem Faixa Ocupacao"),
        coluna(t, "Ordem Faixa Ocupacao", "int64", "Ordenação das faixas de ocupação",
               expr="VAR o = fVoos[taxa_ocupacao] RETURN SWITCH( TRUE(), ISBLANK( o ), 0, o < 0.6, 1, o < 0.75, 2, o < 0.9, 3, 4 )",
               fmt="0"),
    ]
    sel = ", ".join('"%s"' % a for a, _ in RENOMES)
    ren = ",".join('{"%s","%s"}' % p for p in RENOMES)
    m = '''
let
    Colunas = Table.SelectColumns( Fonte, { %s } ),
    Ocupacao = Table.TransformColumns( Colunas, {{"Taxa_Ocupacao_Pct", each _ / 100, type number}} ),
    Renomeado = Table.RenameColumns( Ocupacao, {%s} ),
    OrdemFaixa = Table.AddColumn( Renomeado, "Ordem Faixa Horaria", each
        if [faixa_horaria] = "Manhã" then 1 else if [faixa_horaria] = "Tarde" then 2 else 3, Int64.Type )
in
    OrdemFaixa''' % (sel, ren)
    return tabela(t, "Tabela fato: um registro por voo programado. Só chaves e métricas — atributos descritivos vivem nas dimensões.",
                  "\n".join(c) + "\n" + particao_m(t, "Fato", m))

# ═════════════════════════════ dimensões ═════════════════════════════
def dcalendario():
    t = "dCalendario"
    def cc(nome, tipo, desc, **kw):
        return coluna(t, nome, tipo, desc, src="[%s]" % nome, inferido=True, **kw)
    c = [cc("Date", "dateTime", "Data do calendário", chave=True, fmt="Long Date"),
         cc("Ano", "int64", "Ano civil", fmt="0"),
         cc("Trimestre", "string", "Trimestre do ano (T1 a T4)"),
         cc("Numero do Mes", "int64", "Número do mês, usado para ordenar", fmt="0"),
         cc("Mes", "string", "Mês abreviado (jan, fev…)", ordem="Numero do Mes"),
         cc("Indice Mes", "int64", "AAAAMM, usado para ordenar a competência", fmt="0"),
         cc("Mes Ano", "string", "Competência no formato jan/25", ordem="Indice Mes"),
         cc("Inicio do Mes", "dateTime", "Primeiro dia do mês — eixo contínuo de tempo, que não rola em visual estreito",
            fmt="mmm/yy"),
         cc("Numero Dia Semana", "int64", "Dia da semana (segunda = 1)", fmt="0"),
         cc("Dia da Semana", "string", "Dia da semana por extenso", ordem="Numero Dia Semana")]
    src = '''
VAR _min = MIN( fVoos[data_voo] )
VAR _max = MAX( fVoos[data_voo] )
RETURN
ADDCOLUMNS(
    CALENDAR( DATE( YEAR( _min ), MONTH( _min ), 1 ), EOMONTH( _max, 0 ) ),
    "Ano",               YEAR( [Date] ),
    "Trimestre",         "T" & FORMAT( [Date], "Q" ),
    "Numero do Mes",     MONTH( [Date] ),
    "Mes",               FORMAT( [Date], "MMM", "pt-BR" ),
    "Indice Mes",        YEAR( [Date] ) * 100 + MONTH( [Date] ),
    "Mes Ano",           FORMAT( [Date], "MMM", "pt-BR" ) & "/" & FORMAT( [Date], "yy" ),
    "Inicio do Mes",     DATE( YEAR( [Date] ), MONTH( [Date] ), 1 ),
    "Numero Dia Semana", WEEKDAY( [Date], 2 ),
    "Dia da Semana",     FORMAT( [Date], "dddd", "pt-BR" )
)'''
    part = "\n".join(["\tpartition dCalendario = calculated", "\t\tmode: import", "\t\tsource =", bloco(src, 4), ""])
    return tabela(t, "Dimensão de datas, do primeiro ao último mês presente na fato. Marcada como tabela de datas.",
                  "\n".join(c) + "\n" + part, extra_header="\tdataCategory: Time")

def daeroporto():
    t = "dAeroporto"
    c = [coluna(t, "IATA", "string", "Código IATA do aeroporto", src="IATA", chave=True),
         coluna(t, "Aeroporto", "string", "Rótulo de exibição: código e cidade", src="Aeroporto"),
         coluna(t, "Cidade", "string", "Cidade atendida", src="Cidade", cat="City"),
         coluna(t, "UF", "string", "Unidade da federação", src="UF", cat="StateOrProvince"),
         coluna(t, "Regiao", "string", "Região do país", src="Regiao")]
    m = '''
let
    Origem = Table.RenameColumns( Table.SelectColumns( Fonte, {"Aeroporto_Origem", "Cidade_Origem", "UF_Origem"} ),
        {{"Aeroporto_Origem","IATA"},{"Cidade_Origem","Cidade"},{"UF_Origem","UF"}} ),
    Destino = Table.RenameColumns( Table.SelectColumns( Fonte, {"Aeroporto_Destino", "Cidade_Destino", "UF_Destino"} ),
        {{"Aeroporto_Destino","IATA"},{"Cidade_Destino","Cidade"},{"UF_Destino","UF"}} ),
    Unicos = Table.Distinct( Table.Combine( {Origem, Destino} ), {"IATA"} ),
    Regiao = Table.AddColumn( Unicos, "Regiao", each
        if List.Contains( {"SP","RJ","MG","ES"}, [UF] ) then "Sudeste"
        else if List.Contains( {"PR","SC","RS"}, [UF] ) then "Sul"
        else if List.Contains( {"DF","GO","MT","MS"}, [UF] ) then "Centro-Oeste"
        else if List.Contains( {"AM","PA","AC","RO","RR","AP","TO"}, [UF] ) then "Norte"
        else "Nordeste", type text ),
    Rotulo = Table.AddColumn( Regiao, "Aeroporto", each [IATA] & " · " & [Cidade], type text ),
    Ordenado = Table.Sort( Rotulo, {{"IATA", Order.Ascending}} )
in
    Ordenado'''
    return tabela(t, "Dimensão de aeroportos — união de origens e destinos, para nenhum aeroporto ficar de fora.",
                  "\n".join(c) + "\n" + particao_m(t, "Dimensoes", m))

def drota():
    t = "dRota"
    c = [coluna(t, "Rota", "string", "Par origem-destino, ex.: GRU - BSB", src="Rota", chave=True),
         coluna(t, "Origem IATA", "string", "Código do aeroporto de partida", src="Origem IATA"),
         coluna(t, "Destino IATA", "string", "Código do aeroporto de chegada", src="Destino IATA"),
         coluna(t, "Trecho", "string", "Rota por extenso, cidade a cidade", src="Trecho"),
         coluna(t, "Distancia", "int64", "Extensão da rota em km", src="Distancia", fmt=INT),
         coluna(t, "Faixa de Distancia", "string", "Agrupa as rotas por extensão",
                expr='SWITCH( TRUE(), dRota[Distancia] < 500, "Curta (até 500 km)", dRota[Distancia] < 1500, "Média (500 a 1.500 km)", "Longa (1.500 km ou mais)" )',
                ordem="Ordem Faixa Distancia"),
         coluna(t, "Ordem Faixa Distancia", "int64", "Ordenação das faixas de distância",
                expr="SWITCH( TRUE(), dRota[Distancia] < 500, 1, dRota[Distancia] < 1500, 2, 3 )", fmt="0")]
    m = '''
let
    Cols = Table.SelectColumns( Fonte, {"Rota", "Aeroporto_Origem", "Aeroporto_Destino", "Cidade_Origem", "Cidade_Destino", "Distancia_Km"} ),
    Unicos = Table.Distinct( Cols, {"Rota"} ),
    Trecho = Table.AddColumn( Unicos, "Trecho", each [Cidade_Origem] & " → " & [Cidade_Destino], type text ),
    Enxuto = Table.RemoveColumns( Trecho, {"Cidade_Origem", "Cidade_Destino"} ),
    Renomeado = Table.RenameColumns( Enxuto, {{"Aeroporto_Origem","Origem IATA"},{"Aeroporto_Destino","Destino IATA"},{"Distancia_Km","Distancia"}} ),
    Ordenado = Table.Sort( Renomeado, {{"Rota", Order.Ascending}} )
in
    Ordenado'''
    return tabela(t, "Dimensão de rotas: extremos e extensão de cada par atendido.",
                  "\n".join(c) + "\n" + particao_m(t, "Dimensoes", m))

def daeronave():
    t = "dAeronave"
    c = [coluna(t, "Tipo", "string", "Modelo da aeronave", src="Tipo", chave=True),
         coluna(t, "Fabricante", "string", "Airbus, Boeing ou Embraer", src="Fabricante"),
         coluna(t, "Capacidade", "int64", "Assentos da configuração operada", src="Capacidade", fmt=INT),
         coluna(t, "Porte", "string", "Jato regional (E-Jets) ou narrow-body", src="Porte")]
    m = '''
let
    Cols = Table.SelectColumns( Fonte, {"Tipo_Aeronave", "Capacidade_Aeronave"} ),
    Unicos = Table.Distinct( Cols, {"Tipo_Aeronave"} ),
    Renomeado = Table.RenameColumns( Unicos, {{"Tipo_Aeronave","Tipo"},{"Capacidade_Aeronave","Capacidade"}} ),
    Fabricante = Table.AddColumn( Renomeado, "Fabricante", each Text.BeforeDelimiter( [Tipo], " " ), type text ),
    Porte = Table.AddColumn( Fabricante, "Porte", each if [Fabricante] = "Embraer" then "Jato regional" else "Narrow-body", type text )
in
    Porte'''
    return tabela(t, "Dimensão de aeronaves: fabricante, porte e capacidade.",
                  "\n".join(c) + "\n" + particao_m(t, "Dimensoes", m))

def dsituacao():
    t = "dSituacao"
    c = [coluna(t, "Situacao", "string", "Pontual, Atrasado ou Cancelado", src="Situacao", chave=True, ordem="Ordem"),
         coluna(t, "Ordem", "int64", "Pontual = 1, Atrasado = 2, Cancelado = 3", src="Ordem", fmt="0")]
    m = '''
let
    Lista = Table.Distinct( Table.SelectColumns( Fonte, {"Situacao_Voo"} ) ),
    Renomeado = Table.RenameColumns( Lista, {{"Situacao_Voo","Situacao"}} ),
    Ordem = Table.AddColumn( Renomeado, "Ordem", each
        if [Situacao] = "Pontual" then 1 else if [Situacao] = "Atrasado" then 2 else 3, Int64.Type )
in
    Ordem'''
    return tabela(t, "Dimensão de situação do voo. A ordem fixa as legendas em pontual → atrasado → cancelado.",
                  "\n".join(c) + "\n" + particao_m(t, "Dimensoes", m))

def dmotivo():
    t = "dMotivo"
    c = [coluna(t, "Motivo", "string", "Causa registrada do atraso ou cancelamento", src="Motivo", chave=True),
         coluna(t, "Natureza", "string", "Controlável pela companhia, externa, ou sem ocorrência", src="Natureza",
                ordem="Ordem Natureza"),
         coluna(t, "Ordem Natureza", "int64", "Controlável = 1, Externa = 2, Sem ocorrência = 3", src="Ordem Natureza", fmt="0")]
    m = '''
let
    Lista = Table.Distinct( Table.SelectColumns( Fonte, {"Motivo_Ocorrencia"} ) ),
    Renomeado = Table.RenameColumns( Lista, {{"Motivo_Ocorrencia","Motivo"}} ),
    Natureza = Table.AddColumn( Renomeado, "Natureza", each
        if [Motivo] = "Sem ocorrência" then "Sem ocorrência"
        else if List.Contains( {"Condições meteorológicas", "Restrição aeroportuária"}, [Motivo] ) then "Externa"
        else "Controlável", type text ),
    Ordem = Table.AddColumn( Natureza, "Ordem Natureza", each
        if [Natureza] = "Controlável" then 1 else if [Natureza] = "Externa" then 2 else 3, Int64.Type )
in
    Ordem'''
    return tabela(t, "Dimensão de motivos: separa o que a companhia controla do que é externo.",
                  "\n".join(c) + "\n" + particao_m(t, "Dimensoes", m))

# ═════════════════════════════ medidas ═════════════════════════════
OP, PAX, FIN, CTX = "01 Operação", "02 Passageiros", "03 Financeiro", "04 Contexto e cor"
REAL = 'KEEPFILTERS( fVoos[situacao_voo] <> "Cancelado" )'
MEDIDAS = [
    ("Voos Programados", "COUNTROWS( fVoos )", "Todos os voos do período, inclusive os cancelados.", OP, INT),
    ("Voos Realizados", "CALCULATE( [Voos Programados], %s )" % REAL, "Voos que decolaram: pontuais e atrasados.", OP, INT),
    ("Voos Pontuais", 'CALCULATE( [Voos Programados], KEEPFILTERS( fVoos[situacao_voo] = "Pontual" ) )', "Partiram com até 15 min de atraso.", OP, INT),
    ("Voos Atrasados", 'CALCULATE( [Voos Programados], KEEPFILTERS( fVoos[situacao_voo] = "Atrasado" ) )', "Partiram com mais de 15 min de atraso.", OP, INT),
    ("Voos Cancelados", 'CALCULATE( [Voos Programados], KEEPFILTERS( fVoos[situacao_voo] = "Cancelado" ) )', "Programados e não realizados.", OP, INT),
    ("% Pontuais", "DIVIDE( [Voos Pontuais], [Voos Programados] )", "Pontuais sobre programados. Pontuais + atrasados + cancelados = 100%.", OP, PCT),
    ("% Atrasados", "DIVIDE( [Voos Atrasados], [Voos Programados] )", "Atrasados sobre programados.", OP, PCT),
    ("% Cancelados", "DIVIDE( [Voos Cancelados], [Voos Programados] )", "Cancelados sobre programados.", OP, PCT),
    ("Ocorrências", 'CALCULATE( [Voos Programados], KEEPFILTERS( fVoos[situacao_voo] <> "Pontual" ) )', "Voos atrasados ou cancelados — os que têm motivo registrado.", OP, INT),
    ("Atraso Médio (min)", "AVERAGE( fVoos[atraso_min] )", "Média de atraso dos voos realizados. Cancelado tem atraso vazio e não entra na média.", OP, DEC1),
    ("Atraso Médio dos Atrasados (min)", 'CALCULATE( [Atraso Médio (min)], KEEPFILTERS( fVoos[situacao_voo] = "Atrasado" ) )', "Quanto o voo atrasa quando atrasa.", OP, DEC1),
    ("Atraso Médio (rotas 20+ voos)", "IF( [Voos Realizados] >= 20, [Atraso Médio (min)] )",
     "Atraso médio só onde há amostra: em rota com menos de 20 voos realizados no contexto, fica vazio — evita que 1 voo atrasado lidere o ranking.", OP, DEC1),
    ("Movimentos", "[Voos Programados] + CALCULATE( [Voos Programados], USERELATIONSHIP( fVoos[destino_iata], dAeroporto[IATA] ) )",
     "Partidas + chegadas do aeroporto. Usa a relação inativa de destino para a segunda parcela.", OP, INT),

    ("Passageiros", "SUM( fVoos[passageiros] )", "Passageiros transportados.", PAX, INT),
    ("Assentos Ofertados", "CALCULATE( SUM( fVoos[capacidade] ), %s )" % REAL, "Assentos dos voos que decolaram.", PAX, INT),
    ("Taxa de Ocupação", "DIVIDE( [Passageiros], [Assentos Ofertados] )", "Passageiros sobre assentos ofertados — ponderada, não média de percentuais.", PAX, PCT),
    ("Satisfação Média", "AVERAGE( fVoos[satisfacao] )", "Nota média de 1 a 5.", PAX, "0.00"),

    ("Receita", "SUM( fVoos[receita] )", "Receita bruta.", FIN, MOEDA),
    ("Custo Operacional", "SUM( fVoos[custo] )", "Custo operacional, inclusive o dos voos cancelados.", FIN, MOEDA),
    ("Resultado", "[Receita] - [Custo Operacional]", "Lucro (positivo) ou prejuízo (negativo).", FIN, MOEDA),
    ("Margem", "DIVIDE( [Resultado], [Receita] )", "Resultado sobre receita: Σ lucro ÷ Σ receita, nunca média das margens.", FIN, PCT),
    ("Resultado Médio por Voo", "DIVIDE( [Resultado], [Voos Programados] )", "Resultado dividido pelos voos programados.", FIN, MOEDA),
    ("Receita por Passageiro", "DIVIDE( [Receita], [Passageiros] )", "Tarifa média efetivamente realizada.", FIN, '"R$" #,0.00'),
    ("Custo dos Cancelamentos", 'CALCULATE( [Custo Operacional], KEEPFILTERS( fVoos[situacao_voo] = "Cancelado" ) )', "Custo incorrido em voos que não geraram receita.", FIN, MOEDA),

    ("Cor Resultado", 'IF( [Resultado] < 0, "#C8414F", "#2E9B6B" )', "Verde se lucro, vermelho se prejuízo — usada na formatação condicional.", CTX, None),
    ("Contexto Voos", '"de " & FORMAT( [Voos Programados], "#,0" ) & " programados"', "Linha de contexto do cartão de voos.", CTX, None),
    ("Contexto Passageiros", '"ocupação de " & FORMAT( [Taxa de Ocupação], "0.0%" )', "Linha de contexto do cartão de passageiros.", CTX, None),
    ("Contexto Receita", 'FORMAT( [Receita por Passageiro], "R$ #,0" ) & " por passageiro"', "Linha de contexto do cartão de receita.", CTX, None),
    ("Contexto Resultado", '"margem de " & FORMAT( [Margem], "0.0%" )', "Linha de contexto do cartão de resultado.", CTX, None),
    ("Contexto Atrasos", '"atrasa em média " & FORMAT( [Atraso Médio dos Atrasados (min)], "0" ) & " min"', "Linha de contexto do cartão de atrasos.", CTX, None),
    ("Contexto Cancelados", 'FORMAT( [Voos Cancelados], "#,0" ) & " voos · custo de " & FORMAT( [Custo dos Cancelamentos] / 1000000, "R$ 0.0" ) & " mi"',
     "Linha de contexto do cartão de cancelamentos.", CTX, None),
]

def medidas():
    corpo = "\n".join(medida(n, e, d, p, f) for n, e, d, p, f in MEDIDAS)
    return "/// Tabela dedicada às medidas do modelo. Não contém dados.\ntable _Medidas\n\tlineageTag: %s\n\n%s\n" % (
        tag("_Medidas"), corpo.rstrip("\n")) + "\n\tannotation PBI_ResultType = Table\n"

# ═════════════════════════════ arquivos ═════════════════════════════
TABELAS = {"fVoos": fvoos, "dCalendario": dcalendario, "dAeroporto": daeroporto, "dRota": drota,
           "dAeronave": daeronave, "dSituacao": dsituacao, "dMotivo": dmotivo, "_Medidas": medidas}

URL_BASE = "https://raw.githubusercontent.com"
CAMINHO = "guilhermelevi/visualizacao-dados-CEUB-2026/main/03-aviacao-executivo-analitico/dados/companhia_aerea_10mil_voos.csv"
TIPOS = {"ID_Voo": "type text", "Data_Voo": "type date", "Ano": "Int64.Type", "Mes": "Int64.Type",
         "Capacidade_Aeronave": "Int64.Type", "Passageiros": "Int64.Type", "Distancia_Km": "Int64.Type",
         "Duracao_Prevista_Min": "Int64.Type", "Duracao_Real_Min": "Int64.Type", "Atraso_Min": "Int64.Type",
         "Taxa_Ocupacao_Pct": "type number", "Preco_Medio_Passagem_R$": "type number", "Receita_R$": "type number",
         "Custo_Operacional_R$": "type number", "Lucro_R$": "type number", "Margem_Lucro_Pct": "type number",
         "Satisfacao_1a5": "type number"}
CABECALHO = open(os.path.join(AQUI, "dados", "companhia_aerea_10mil_voos.csv"), encoding="utf-8-sig").readline().strip().split(";")

def expressions():
    tipos = ", ".join('{"%s", %s}' % (c, TIPOS.get(c, "type text")) for c in CABECALHO)
    fonte = '''
let
    Conteudo = Web.Contents( pUrlBase, [RelativePath = pCaminhoCSV] ),
    Origem = Csv.Document( Conteudo, [Delimiter = ";", Columns = %d, Encoding = 65001, QuoteStyle = QuoteStyle.Csv] ),
    Cabecalho = Table.PromoteHeaders( Origem, [PromoteAllScalars = true] ),
    Tipos = Table.TransformColumnTypes( Cabecalho, {%s}, "en-US" ),
    SemVazios = Table.SelectRows( Tipos, each [ID_Voo] <> null and [ID_Voo] <> "" )
in
    SemVazios''' % (len(CABECALHO), tipos)
    return "\n".join([
        "/// Host de onde o arquivo de dados é baixado.",
        'expression pUrlBase = "%s" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]' % URL_BASE,
        "\tlineageTag: %s" % tag("expr", "pUrlBase"), "\tqueryGroup: Parametros", "",
        "\tannotation PBI_ResultType = Text", "",
        "/// Caminho do CSV TRATADO (saída de tratar_dados.py) dentro do repositório.",
        'expression pCaminhoCSV = "%s" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]' % CAMINHO,
        "\tlineageTag: %s" % tag("expr", "pCaminhoCSV"), "\tqueryGroup: Parametros", "",
        "\tannotation PBI_ResultType = Text", "",
        "/// Consulta de estágio: lê e tipa o CSV uma vez só. Ponto decimal -> cultura en-US.",
        "expression Fonte =", bloco(fonte, 2),
        "\tlineageTag: %s" % tag("expr", "Fonte"), "\tqueryGroup: Estagio", "",
        "\tannotation PBI_ResultType = Table", ""])

RELACOES = [("rel_calendario_voos", "fVoos.data_voo", "dCalendario.Date", True),
            ("rel_origem_voos", "fVoos.origem_iata", "dAeroporto.IATA", True),
            ("rel_destino_voos", "fVoos.destino_iata", "dAeroporto.IATA", False),
            ("rel_rota_voos", "fVoos.rota", "dRota.Rota", True),
            ("rel_aeronave_voos", "fVoos.tipo_aeronave", "dAeronave.Tipo", True),
            ("rel_situacao_voos", "fVoos.situacao_voo", "dSituacao.Situacao", True),
            ("rel_motivo_voos", "fVoos.motivo", "dMotivo.Motivo", True)]

def relationships():
    # relationship NÃO aceita descrição (///): o import inteiro falha
    out = []
    for nome, de, para, ativa in RELACOES:
        out.append("relationship %s" % nome)
        if not ativa: out.append("\tisActive: false")
        out += ["\tfromColumn: %s" % de, "\ttoColumn: %s" % para, ""]
    return "\n".join(out)

def model():
    return "\n".join(["model Model", "\tculture: pt-BR", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
                      "\tsourceQueryCulture: pt-BR", "\tdataAccessOptions", "\t\tlegacyRedirects",
                      "\t\treturnErrorValuesAsNull", "",
                      "queryGroup Parametros", "", "queryGroup Fato", "", "queryGroup Dimensoes", "",
                      "queryGroup Estagio", "", "annotation __PBI_TimeIntelligenceEnabled = 0", ""] +
                     ["ref table %s" % t for t in TABELAS] + ["", "ref cultureInfo pt-BR", ""])

def escrever(caminho, texto):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="\n") as fh: fh.write(texto)

if __name__ == "__main__":
    shutil.rmtree(os.path.join(DEF, "tables"), ignore_errors=True)
    escrever(os.path.join(DEF, "database.tmdl"), "database\n\tcompatibilityLevel: 1567\n\n")
    escrever(os.path.join(DEF, "model.tmdl"), model())
    escrever(os.path.join(DEF, "expressions.tmdl"), expressions())
    escrever(os.path.join(DEF, "relationships.tmdl"), relationships())
    escrever(os.path.join(DEF, "cultures", "pt-BR.tmdl"),
             'cultureInfo pt-BR\n\n\tlinguisticMetadata =\n\t\t\t{\n\t\t\t  "Version": "1.0.0",\n'
             '\t\t\t  "Language": "pt-BR"\n\t\t\t}\n\t\tcontentType: json\n\n')
    for nome, fn in TABELAS.items():
        escrever(os.path.join(DEF, "tables", "%s.tmdl" % nome), fn())
    escrever(os.path.join(SM, "definition.pbism"),
             '{\n  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",\n'
             '  "version": "4.2",\n  "settings": {}\n}\n')
    escrever(os.path.join(SM, ".platform"),
             '{\n  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",\n'
             '  "metadata": {\n    "type": "SemanticModel",\n    "displayName": "PainelAviacao"\n  },\n'
             '  "config": {\n    "version": "2.0",\n    "logicalId": "%s"\n  }\n}\n' % tag("logical", "model"))
    print("modelo: %d tabelas, %d medidas, %d relações" % (len(TABELAS), len(MEDIDAS), len(RELACOES)))
