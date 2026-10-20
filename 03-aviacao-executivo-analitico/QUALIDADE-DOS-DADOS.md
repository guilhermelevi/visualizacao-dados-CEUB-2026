# Qualidade dos dados — companhia_aerea_10mil_voos.csv

> Gerado por `tratar_dados.py`. Não edite à mão: rode o script de novo.

**Dados simulados**, gerados para o exercício — não representam uma companhia real.

| | |
|---|---|
| Registros | 10.000 |
| Período | 01/01/2025 a 30/09/2026 |
| Colunas | 31 |
| Rotas · aeroportos · aeronaves | 180 · 14 · 5 |
| Formato | `;` como separador, **ponto** decimal, UTF-8 |

## 1. Erros encontrados e corrigidos

Todos nos **382 voos cancelados**. O arquivo bruto preenche com valor campos que, para um voo que não decolou, **não se aplicam**. A correção é deixá-los vazios: o Power BI ignora vazio nas médias, mas conta zero como medição.

| Coluna | O bruto trazia | Linhas corrigidas | Efeito se não corrigir |
|---|---|---|---|
| `Atraso_Min` | 0 min de atraso | 382 | A média de atraso cai de 21,0 para 20,2 min — 382 voos que não decolaram contam como pontuais no relógio. |
| `Duracao_Real_Min` | 0 min de voo | 382 | Duração média real fica 4% menor do que foi de fato. |
| `Taxa_Ocupacao_Pct` | 0% de ocupação | 382 | A ocupação média simples cai de 75,3% para 72,4% — avião que não voou não estava vazio. |
| `Preco_Medio_Passagem_R$` | preço de passagem preenchido sem nenhum passageiro | 382 | Preço médio sem venda que o sustente; contradiz Receita = 0. |
| `Margem_Lucro_Pct` | margem 0% com receita 0 e lucro negativo | 382 | Margem sobre receita zero é indefinida, não zero; a média simples de margem cai de 71,4% para 68,7%. |

Mantidos como estão nos cancelados, porque são zeros **verdadeiros**: `Passageiros = 0` e `Receita_R$ = 0` (ninguém voou, nada foi faturado), `Custo_Operacional_R$` e `Lucro_R$` negativo (o custo do cancelamento existiu).

## 2. Regras de integridade conferidas

| Regra | Violações |
|---|---|
| Campo vazio ou com espaço sobrando | 0 ✓ |
| ID_Voo duplicado | 0 ✓ |
| Ano, Mes, Ano_Mes ou Dia_Semana divergem de Data_Voo | 0 ✓ |
| Faixa_Horaria diverge de Horario_Partida | 0 ✓ |
| Origem igual ao destino | 0 ✓ |
| Rota diferente de 'ORIGEM - DESTINO' | 0 ✓ |
| Passageiros acima da capacidade | 0 ✓ |
| Valor negativo em contagem, distância, duração ou custo | 0 ✓ |
| Pontual com atraso acima de 15 min | 0 ✓ |
| Atrasado com atraso de até 15 min | 0 ✓ |
| Pontual com motivo de ocorrência, ou atrasado/cancelado sem motivo | 0 ✓ |
| Cancelado com passageiros ou receita | 0 ✓ |
| Taxa de ocupação diferente de passageiros / capacidade (tolerância 0,01 p.p.) | 0 ✓ |
| Receita diferente de passageiros × preço médio (tolerância R$ 1) | 0 ✓ |
| Lucro diferente de receita − custo (tolerância R$ 0,01) | 0 ✓ |
| Margem diferente de lucro / receita (tolerância 0,01 p.p.) | 0 ✓ |
| Satisfação fora da escala 1 a 5 | 0 ✓ |
| Aeroporto com mais de uma cidade/UF | 0 ✓ |
| Aeronave com mais de uma capacidade | 0 ✓ |
| Rota com mais de uma distância | 0 ✓ |

## 3. Pontos de atenção (não são erro, mas mudam a leitura)

- **Rotas com poucos voos.** 77 das 180 rotas têm menos de 20 voos no período (a menor tem 1). Uma média de atraso sobre 2 ou 3 voos não é comparável com a de uma rota de 600: por isso o ranking de atraso por rota considera só rotas com **20 voos ou mais**.
- **Satisfação em voo cancelado.** Os cancelados têm `Passageiros = 0`, mas nota média de satisfação 1.67. Interpretado como a avaliação dos passageiros remanejados — por isso a nota foi mantida. Se a premissa não valer, basta excluir os cancelados da medida.
- **Taxa de ocupação** vem em escala 0–100; o modelo divide por 100 para formatar como %.
- **Margem por linha não é somável.** O modelo recalcula a margem como `Σ lucro ÷ Σ receita`, nunca como média das margens das linhas.

## 4. Resultado

Nenhuma regra de integridade violada. Após a correção da seção 1, o arquivo `dados/companhia_aerea_10mil_voos.csv` está pronto para o modelo.
