# -*- coding: utf-8 -*-
"""
Audita e corrige o CSV de voos antes de ele entrar no modelo.

    python3 tratar_dados.py

Lê   dados/bruto/companhia_aerea_10mil_voos.csv   (nunca é alterado)
Gera dados/companhia_aerea_10mil_voos.csv          (o que o modelo lê)
     QUALIDADE-DOS-DADOS.md                        (o que foi checado e corrigido)

Trabalha nas strings do arquivo, não em DataFrame: o que não é corrigido sai
byte a byte igual ao bruto (sem 9 virar 9.0, sem arredondamento de float).
Sai com código 1 se encontrar erro que não sabe corrigir.
"""
import csv, os, sys
from collections import Counter
from datetime import date

AQUI = os.path.dirname(os.path.abspath(__file__))
BRUTO = os.path.join(AQUI, "dados", "bruto", "companhia_aerea_10mil_voos.csv")
TRATADO = os.path.join(AQUI, "dados", "companhia_aerea_10mil_voos.csv")
RELATORIO = os.path.join(AQUI, "QUALIDADE-DOS-DADOS.md")

DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

def f(x):
    return float(x)

def faixa_horaria(hhmm):
    h = int(hhmm[:2])
    return "Manhã" if h < 12 else "Tarde" if h < 18 else "Noite"

with open(BRUTO, encoding="utf-8-sig", newline="") as fh:
    rd = csv.DictReader(fh, delimiter=";")
    COLS = rd.fieldnames
    rows = list(rd)

# ── 1. regras de integridade: cada uma devolve os IDs que a violam ──────────
#     Estas não têm correção automática — se alguma falhar, o script para.
def viola(pred):
    return [r["ID_Voo"] for r in rows if pred(r)]

ids = Counter(r["ID_Voo"] for r in rows)
REGRAS = [
    ("Campo vazio ou com espaço sobrando",
     viola(lambda r: any(v is None or v != v.strip() or v == "" for v in r.values()))),
    ("ID_Voo duplicado", [i for i, n in ids.items() if n > 1]),
    ("Ano, Mes, Ano_Mes ou Dia_Semana divergem de Data_Voo",
     viola(lambda r: (lambda d: (int(r["Ano"]), int(r["Mes"]), r["Ano_Mes"], r["Dia_Semana"])
                     != (d.year, d.month, d.strftime("%Y-%m"), DIAS[d.weekday()]))
           (date.fromisoformat(r["Data_Voo"])))),
    ("Faixa_Horaria diverge de Horario_Partida",
     viola(lambda r: faixa_horaria(r["Horario_Partida"]) != r["Faixa_Horaria"])),
    ("Origem igual ao destino", viola(lambda r: r["Aeroporto_Origem"] == r["Aeroporto_Destino"])),
    ("Rota diferente de 'ORIGEM - DESTINO'",
     viola(lambda r: r["Rota"] != "%s - %s" % (r["Aeroporto_Origem"], r["Aeroporto_Destino"]))),
    ("Passageiros acima da capacidade",
     viola(lambda r: int(r["Passageiros"]) > int(r["Capacidade_Aeronave"]))),
    ("Valor negativo em contagem, distância, duração ou custo",
     viola(lambda r: min(f(r[c]) for c in ("Passageiros", "Capacidade_Aeronave", "Distancia_Km",
                         "Duracao_Prevista_Min", "Duracao_Real_Min", "Atraso_Min",
                         "Custo_Operacional_R$")) < 0)),
    ("Pontual com atraso acima de 15 min",
     viola(lambda r: r["Situacao_Voo"] == "Pontual" and f(r["Atraso_Min"]) > 15)),
    ("Atrasado com atraso de até 15 min",
     viola(lambda r: r["Situacao_Voo"] == "Atrasado" and f(r["Atraso_Min"]) <= 15)),
    ("Pontual com motivo de ocorrência, ou atrasado/cancelado sem motivo",
     viola(lambda r: (r["Situacao_Voo"] == "Pontual") != (r["Motivo_Ocorrencia"] == "Sem ocorrência"))),
    ("Cancelado com passageiros ou receita",
     viola(lambda r: r["Situacao_Voo"] == "Cancelado"
           and (int(r["Passageiros"]) > 0 or f(r["Receita_R$"]) > 0))),
    ("Taxa de ocupação diferente de passageiros / capacidade (tolerância 0,01 p.p.)",
     viola(lambda r: r["Situacao_Voo"] != "Cancelado" and
           abs(int(r["Passageiros"]) / int(r["Capacidade_Aeronave"]) * 100 - f(r["Taxa_Ocupacao_Pct"])) > 0.01)),
    ("Receita diferente de passageiros × preço médio (tolerância R$ 1)",
     viola(lambda r: r["Situacao_Voo"] != "Cancelado" and
           abs(int(r["Passageiros"]) * f(r["Preco_Medio_Passagem_R$"]) - f(r["Receita_R$"])) > 1)),
    ("Lucro diferente de receita − custo (tolerância R$ 0,01)",
     viola(lambda r: abs(f(r["Receita_R$"]) - f(r["Custo_Operacional_R$"]) - f(r["Lucro_R$"])) > 0.011)),
    ("Margem diferente de lucro / receita (tolerância 0,01 p.p.)",
     viola(lambda r: f(r["Receita_R$"]) > 0 and
           abs(f(r["Lucro_R$"]) / f(r["Receita_R$"]) * 100 - f(r["Margem_Lucro_Pct"])) > 0.01)),
    ("Satisfação fora da escala 1 a 5",
     viola(lambda r: not 1 <= f(r["Satisfacao_1a5"]) <= 5)),
]

# atributos que precisam ser constantes por entidade (senão a dimensão sai duplicada)
def constante(chave, attrs):
    vistos = {}
    for r in rows:
        for lado in chave:
            k = r[lado]
            v = tuple(r[a.replace("*", lado.split("_")[-1])] for a in attrs)
            vistos.setdefault(k, set()).add(v)
    return [k for k, v in vistos.items() if len(v) > 1]

REGRAS += [
    ("Aeroporto com mais de uma cidade/UF",
     constante(("Aeroporto_Origem", "Aeroporto_Destino"), ("Cidade_*", "UF_*"))),
    ("Aeronave com mais de uma capacidade",
     [k for k, v in {t: {r["Capacidade_Aeronave"] for r in rows if r["Tipo_Aeronave"] == t}
                     for t in {r["Tipo_Aeronave"] for r in rows}}.items() if len(v) > 1]),
    ("Rota com mais de uma distância",
     [k for k, v in {t: {r["Distancia_Km"] for r in rows if r["Rota"] == t}
                     for t in {r["Rota"] for r in rows}}.items() if len(v) > 1]),
]

# ── 2. erros com correção conhecida ─────────────────────────────────────────
#     Voo cancelado não decolou: atraso, duração real, ocupação, preço praticado
#     e margem NÃO SE APLICAM. O bruto grava 0 (ou um preço) nesses campos, e um
#     zero entra em toda média como se fosse medido. Corrigir = deixar vazio.
CORRECOES = [
    ("Atraso_Min", "0 min de atraso",
     "A média de atraso cai de 21,0 para 20,2 min — 382 voos que não decolaram contam como pontuais no relógio."),
    ("Duracao_Real_Min", "0 min de voo",
     "Duração média real fica 4% menor do que foi de fato."),
    ("Taxa_Ocupacao_Pct", "0% de ocupação",
     "A ocupação média simples cai de 75,3% para 72,4% — avião que não voou não estava vazio."),
    ("Preco_Medio_Passagem_R$", "preço de passagem preenchido sem nenhum passageiro",
     "Preço médio sem venda que o sustente; contradiz Receita = 0."),
    ("Margem_Lucro_Pct", "margem 0% com receita 0 e lucro negativo",
     "Margem sobre receita zero é indefinida, não zero; a média simples de margem cai de 71,4% para 68,7%."),
]
alterados = Counter()
for r in rows:
    if r["Situacao_Voo"] != "Cancelado": continue
    for col, _, _ in CORRECOES:
        if r[col] != "":
            r[col] = ""
            alterados[col] += 1

# ── 3. pontos de atenção: não são erro, mas mudam a leitura ─────────────────
cancel = [r for r in rows if r["Situacao_Voo"] == "Cancelado"]
voos_rota = Counter(r["Rota"] for r in rows)
pequenas = sum(1 for n in voos_rota.values() if n < 20)
sat_cancel = sum(f(r["Satisfacao_1a5"]) for r in cancel) / len(cancel)

# ── 4. saída ────────────────────────────────────────────────────────────────
falhas = [(n, v) for n, v in REGRAS if v]
with open(TRATADO, "w", encoding="utf-8", newline="") as fh:
    wr = csv.DictWriter(fh, fieldnames=COLS, delimiter=";", lineterminator="\n")
    wr.writeheader(); wr.writerows(rows)

L = []
L.append("# Qualidade dos dados — companhia_aerea_10mil_voos.csv\n")
L.append("> Gerado por `tratar_dados.py`. Não edite à mão: rode o script de novo.\n")
L.append("**Dados simulados**, gerados para o exercício — não representam uma companhia real.\n")
L.append("| | |\n|---|---|")
L.append("| Registros | %s |" % format(len(rows), ",").replace(",", "."))
L.append("| Período | %s a %s |" % tuple(date.fromisoformat(d).strftime("%d/%m/%Y")
                                    for d in (min(r["Data_Voo"] for r in rows), max(r["Data_Voo"] for r in rows))))
L.append("| Colunas | %d |" % len(COLS))
L.append("| Rotas · aeroportos · aeronaves | %d · %d · %d |" % (
    len(voos_rota), len({r["Aeroporto_Origem"] for r in rows} | {r["Aeroporto_Destino"] for r in rows}),
    len({r["Tipo_Aeronave"] for r in rows})))
L.append("| Formato | `;` como separador, **ponto** decimal, UTF-8 |\n")

L.append("## 1. Erros encontrados e corrigidos\n")
L.append("Todos nos **%d voos cancelados**. O arquivo bruto preenche com valor campos que, para "
         "um voo que não decolou, **não se aplicam**. A correção é deixá-los vazios: o Power BI "
         "ignora vazio nas médias, mas conta zero como medição.\n" % len(cancel))
L.append("| Coluna | O bruto trazia | Linhas corrigidas | Efeito se não corrigir |\n|---|---|---|---|")
for col, era, efeito in CORRECOES:
    L.append("| `%s` | %s | %d | %s |" % (col, era, alterados[col], efeito))
L.append("\nMantidos como estão nos cancelados, porque são zeros **verdadeiros**: `Passageiros = 0` "
         "e `Receita_R$ = 0` (ninguém voou, nada foi faturado), `Custo_Operacional_R$` e "
         "`Lucro_R$` negativo (o custo do cancelamento existiu).\n")

L.append("## 2. Regras de integridade conferidas\n")
L.append("| Regra | Violações |\n|---|---|")
for nome, v in REGRAS:
    L.append("| %s | %s |" % (nome, "**%d** ✗" % len(v) if v else "0 ✓"))
L.append("")

L.append("## 3. Pontos de atenção (não são erro, mas mudam a leitura)\n")
L.append("- **Rotas com poucos voos.** %d das %d rotas têm menos de 20 voos no período (a menor tem %d). "
         "Uma média de atraso sobre 2 ou 3 voos não é comparável com a de uma rota de 600: "
         "por isso o ranking de atraso por rota considera só rotas com **20 voos ou mais**."
         % (pequenas, len(voos_rota), min(voos_rota.values())))
L.append("- **Satisfação em voo cancelado.** Os cancelados têm `Passageiros = 0`, mas nota média "
         "de satisfação %.2f. Interpretado como a avaliação dos passageiros remanejados — por isso "
         "a nota foi mantida. Se a premissa não valer, basta excluir os cancelados da medida."
         % sat_cancel)
L.append("- **Taxa de ocupação** vem em escala 0–100; o modelo divide por 100 para formatar como %.")
L.append("- **Margem por linha não é somável.** O modelo recalcula a margem como "
         "`Σ lucro ÷ Σ receita`, nunca como média das margens das linhas.\n")

L.append("## 4. Resultado\n")
if falhas:
    L.append("**%d regra(s) violada(s) sem correção automática** — investigar antes de usar.\n" % len(falhas))
else:
    L.append("Nenhuma regra de integridade violada. Após a correção da seção 1, o arquivo "
             "`dados/companhia_aerea_10mil_voos.csv` está pronto para o modelo.\n")
open(RELATORIO, "w", encoding="utf-8").write("\n".join(L))

print("linhas: %d  ·  cancelados: %d" % (len(rows), len(cancel)))
for col, _, _ in CORRECOES:
    print("  corrigido %-24s %4d" % (col, alterados[col]))
for nome, v in REGRAS:
    print("  %s %s%s" % ("✗" if v else "✓", nome, " (%d)" % len(v) if v else ""))
print("→ %s\n→ %s" % (os.path.relpath(TRATADO, AQUI), os.path.relpath(RELATORIO, AQUI)))
sys.exit(1 if falhas else 0)
