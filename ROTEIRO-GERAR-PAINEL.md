# Roteiro — gerar um painel do zero

Playbook para produzir um dashboard completo a partir de um enunciado.
Escrito depois de construir o painel da companhia aérea; as armadilhas listadas aqui
são as que realmente apareceram, não as que a documentação avisa.

---

## 1. O que me mandar

O mínimo:

- **O enunciado** (PDF, print ou texto colado). Eu leio inteiro antes de começar.
- **Os dados**, se já existirem. Se não, eu gero — diga o tema e o volume.

Se souber, diga também:

| Informação | Por que muda o resultado |
|---|---|
| Onde vai rodar | Fabric online, Desktop, ou só um HTML local — muda tudo |
| Se precisa entregar `.pbix` | Define se dá para publicar por API ou precisa de Desktop |
| Prazo | Define se vale caprichar no visual ou entregar o essencial |
| Se a interface está em inglês | Para eu dar os nomes certos dos botões |

Se não disser nada, eu assumo Fabric online e pergunto só o que for bloqueante.

---

## 2. O que eu faço, em ordem

### Etapa 1 — Ler e mapear

Leio o enunciado e monto uma **tabela de cobertura**: cada pergunta → qual visual
responde → por quê. Essa tabela vira um `.md` na entrega, porque a justificativa da
escolha do gráfico costuma valer nota.

Também extraio a lista de requisitos técnicos (mínimo de visuais, de KPIs, de filtros)
e trato como checklist.

### Etapa 2 — Dados

Se o dataset não existe, eu gero com variação realista: sazonalidade, outliers,
categorias com pesos diferentes, alguns valores extremos. Datasets onde tudo se
comporta igual não respondem perguntas analíticas.

Se já existe, **eu valido antes de modelar**: contagem, período, distribuições,
percentual de nulos, cardinalidade. Isso evita descobrir na última hora que 30% de
uma coluna está vazia.

#### Verificar erros no CSV — e corrigir, sempre

Perfil estatístico não basta: um arquivo sem nulo nenhum ainda pode estar errado.
**Todo CSV passa por uma auditoria de erros antes de entrar no modelo, e todo erro
encontrado é corrigido** — painel construído sobre dado errado responde a pergunta
errada, por mais bonito que fique. Erro conhecido e não corrigido não é aceitável,
nem com nota de rodapé.

Como fazer:

1. **Preservar o bruto.** O arquivo recebido vai para `dados/bruto/` e nunca é editado.
2. **Corrigir por script, nunca à mão.** Um `tratar_dados.py` lê o bruto, confere as
   regras, aplica as correções e grava o arquivo tratado em `dados/` — que é o único que
   o modelo lê. Rodar de novo produz o mesmo resultado.
3. **Corrigir só o que está errado.** O script trabalha nas strings: linha sem erro sai
   byte a byte igual ao bruto (sem `9` virar `9.0`). Conferir com `diff` quantas linhas mudaram.
4. **Registrar.** O script gera `QUALIDADE-DOS-DADOS.md`: cada erro, quantas linhas, a
   correção aplicada e o efeito que teria no painel. Vai junto na entrega.
5. **Parar se não souber corrigir.** Regra violada sem correção conhecida faz o script sair
   com erro — aí é investigar e decidir, não seguir em frente.

O que conferir, no mínimo:

| Tipo | Exemplos de regra |
|---|---|
| Unicidade | ID duplicado; linha duplicada com IDs diferentes |
| Coerência de datas | `Ano`, `Mes`, `Ano_Mes`, dia da semana batem com a data; faixa horária bate com o horário |
| Coerência de chaves | rota = `ORIGEM - DESTINO`; origem ≠ destino; cada código tem uma cidade/UF só; cada aeronave uma capacidade só |
| Limites | contagem ≤ capacidade; nada negativo onde não pode; notas dentro da escala |
| Contas derivadas | ocupação = passageiros ÷ capacidade; receita = passageiros × preço; lucro = receita − custo; margem = lucro ÷ receita |
| Regra de negócio | pontual ≤ 15 min e atrasado > 15 min; pontual sem motivo, atrasado/cancelado com motivo |
| **"Não se aplica" gravado como valor** | campo que não existe para aquela linha vindo preenchido (ver abaixo) |

> **O erro mais traiçoeiro é o zero que significa "não se aplica".** No CSV de 10 mil voos
> (exercício 03), os 382 cancelados vinham com `Atraso_Min = 0`, `Taxa_Ocupacao_Pct = 0`,
> `Duracao_Real_Min = 0`, margem `0%` e um preço de passagem sem nenhum passageiro. Nenhuma
> checagem de nulo pega isso — não há nulo. Mas todo zero entra na média como se fosse
> medido: o atraso médio caía de 21,0 para 20,2 min e a ocupação de 75,3% para 72,4%. A
> correção é **deixar vazio**: o Power BI ignora vazio nas médias e conta zero.
> Zero verdadeiro (passageiros = 0, receita = 0 no cancelado) fica como está.

Também anote o que **não é erro mas muda a leitura**: amostra pequena (rota com 1 voo
lidera qualquer ranking de média — exija um mínimo de voos na medida), escala de
percentual 0–100 vs 0–1, colunas por linha que não são somáveis (margem, ocupação).

### Etapa 3 — Modelo

Star schema de verdade: **a fato guarda apenas chaves estrangeiras e métricas**. Todo
atributo descritivo vai para uma dimensão.

O teste é simples: se a coluna descreve *o que a entidade é* (cidade, região, fabricante,
porte, natureza da causa), ela pertence à dimensão. Se ela mede *o que aconteceu naquela
linha* (passageiros, receita, atraso), fica na fato.

A exceção são as **faixas derivadas da própria linha** — faixa de atraso, faixa de
ocupação, resultado do voo. Dependem do valor medido naquele registro, não de um atributo
compartilhado, então ficam na fato mesmo sendo texto.

> É fácil produzir uma flat table e chamá-la de star schema. Se a fato tem 40 colunas e
> só duas dimensões penduradas, não é star schema — é uma tabela larga. O sinal mais claro
> é encontrar `cidade`, `uf`, `região` ou `ano/mês/dia` dentro da fato.

Demais regras:

- Calendário próprio, marcado como tabela de datas (nunca a hierarquia automática)
- Uma **consulta de estágio** que lê e tipa o arquivo **uma vez só**; a fato e as dimensões
  derivam dela. Sem isso, sete tabelas baixam o mesmo arquivo sete vezes no refresh
- Dimensão de local deve cobrir origem **e** destino: unir os dois conjuntos antes do
  `Table.Distinct`
- Medidas em DAX, agrupadas em pastas por assunto
- Descrição em toda medida e coluna — vira tooltip e ajuda na apresentação
- Colunas de ordenação (`sortByColumn`) nas dimensões: fazem legendas e eixos saírem na
  ordem lógica em vez de alfabética, de graça

### Etapa 4 — Visual

Layout em camadas, de cima para baixo: **título e filtros → KPIs → análises → detalhamento**.

**Cor é codificação, não decoração.** Toda cor no painel precisa responder "o que ela
significa?". Se a resposta for "só pra não ficar tudo igual", a cor está errada — tire.

| Cor | Significa |
|---|---|
| Azul escuro | institucional, neutro |
| Verde | positivo (lucro, pontualidade) |
| Âmbar | atenção (atrasos) |
| Vermelho | negativo (cancelamento, prejuízo) |
| Cinza | secundário, apoio |

Três regras que saem daí:

1. **Mesmo significado, mesma cor, no painel inteiro.** Se atraso é âmbar no gráfico de
   barras, é âmbar no KPI, na linha do tempo e na matriz. Categoria que muda de cor entre
   visuais faz o leitor reaprender a legenda a cada olhada.
2. **Categoria sem julgamento → uma cor só.** Região, mês, modelo, especialidade: nada ali
   é bom nem ruim, então nada ali merece matiz próprio. Um matiz único e, quando a
   grandeza importa, uma rampa de luminosidade dentro dele — escuro = mais, claro = menos.
   Isso é o oposto de dar um matiz a cada retângulo (ver *Treemap ignora cor por valor*).
3. **Não colorir o que o eixo já diz.** Barra por categoria com uma cor por barra é
   redundância: o rótulo já identifica. Reserve a cor para a única dimensão que ela ainda
   não está carregando.

Na prática: define a cor visual a visual, nunca confiando no tema (ver *Tema custom pela
API não resolve o arquivo*), e derivando de uma paleta única no código — assim a mesma
constante `VERDE` vai para todo lugar que significa "positivo".

Todo visual leva título e subtítulo dizendo **qual pergunta responde**.

Medidas que valem lembrar: um slicer em dropdown precisa de **~50px de altura** para o
cabeçalho e a caixa caberem — com menos, o dropdown sai cortado. A faixa de título que
os abriga precisa de ~80px.

### Etapa 5 — Publicar

No Fabric, pela REST API — não precisa de Git integration nem de Desktop:

```
POST /v1/workspaces/{ws}/semanticModels     ← cria o modelo (TMDL em base64)
POST /v1/workspaces/{ws}/reports            ← cria o relatório (PBIR em base64)
PATCH /v1.0/myorg/gateways/{gw}/datasources/{ds}   ← credencial
POST /v1.0/myorg/groups/{ws}/datasets/{id}/refreshes
```

Autenticação sem instalar nada, via device code:

```bash
curl -X POST "https://login.microsoftonline.com/common/oauth2/v2.0/devicecode" \
  -d "client_id=04b07795-8ddb-461a-bbee-02f9e1bf7b46" \
  -d "scope=https://api.fabric.microsoft.com/.default offline_access"
```

Você abre o link, digita o código, e eu sigo daí.

### Etapa 6 — Validar de verdade

A validação tem **duas camadas**, e confundi-las é o erro mais caro do processo.

#### Camada 1 — estrutural, roda local, antes de publicar

Um script `validar.py` na raiz do projeto. Ele pega o que **passa no import e quebra em
silêncio**:

- todo campo referenciado em cada `visual.json` existe mesmo no modelo (tabela, coluna, medida)
- os schemas do PBIR estão nas versões que renderizam (ver tabela em *Armadilhas*)
- nenhum visual extrapola a página, tem dimensão zero ou se sobrepõe na mesma camada `z`
- `sourceColumn` usa o nome **depois** do `Table.RenameColumns`
- todo visual autônomo tem título explicativo
- todo JSON do projeto é parseável
- os relacionamentos apontam para colunas que existem

É barato, roda em segundo e pega erro de digitação em nome de medida — que no Fabric
aparece como visual vazio, sem mensagem.

#### Camada 2 — de renderização, só existe depois de publicar

**`validar.py` não sabe se o painel desenha.** Ele confere estrutura, não pixels. Um
treemap pode passar em tudo e sair ilegível. Três checagens, nessa ordem:

1. **Consulta DAX** (`/executeQueries`) — confere se os números batem com a análise local.
   Depois de refatorar o modelo, rodar os mesmos KPIs antes e depois: se algum número
   mudou, a refatoração quebrou alguma relação
2. **Export PDF** (`/ExportTo`) — se travar em 0%, o relatório está quebrado
3. **Eu leio o PDF** e olho cada visual

A terceira é a que pega mais coisa. No painel aéreo ela revelou o mapa com erro,
formas com a cor errada e categorias esmagando o gráfico — nada disso aparece em log.

> **Não diga que está pronto antes da camada 2.** Projeto que passou só na camada 1 está
> *construído e conferido*, não *validado*. A diferença é honesta e importa.

### Etapa 7 — conferir os números que você afirma

Todo insight escrito no painel é uma afirmação sobre os dados, e precisa ser recalculado
contra a fonte antes de entrar. No painel hospitalar eu escrevi que uma especialidade
superava "as outras seis somadas" — a soma dava 44.872 contra 24.174. Só apareceu porque
rodei a conta.

Afirmação em dashboard não é texto de apoio: é resultado. Trate como tal.

---

## 3. Armadilhas (custaram tempo de verdade)

### Formato PBIR

Schemas `1.0.0` **são aceitos no import e não renderizam**. O relatório abre em branco,
com skeleton infinito, e o export trava em 0% sem mensagem de erro.

| Arquivo | Versão que funciona |
|---|---|
| `definition.pbir` | `report/definitionProperties/2.0.0` — sem `/definition/` no caminho |
| `definition/version.json` | campo `version: "2.0.0"` |
| `definition/report.json` | `report/3.3.0` |
| `pages/<p>/page.json` | `page/2.1.0` |
| `visuals/<v>/visual.json` | `visualContainer/2.12.0` |
| `pages/pages.json` | `pagesMetadata/1.1.0` |

> **Como descobrir a versão certa a qualquer momento:** criar um relatório trivial pela
> interface do Fabric e baixar sua definição com
> `POST /v1/workspaces/{ws}/reports/{id}/getDefinition`. Esse é o gabarito. Não confie
> na documentação, que fica atrás da versão em produção.

### Outras que quebram em silêncio

- `themeCollection` é obrigatório. O `baseTheme` precisa do **arquivo físico** em
  `StaticResources/SharedResources/BaseThemes/`, e `reportVersionAtImport` é um
  **objeto** `{visual, report, page}`, não uma string.
- `byConnection` moderno tem só `connectionString`, terminando em `semanticmodelid=<guid>`.
- Visuais `shape` **ignoram** a cor que você define. Use `textbox` com
  `visualContainerObjects.background`.
- Mapas exigem Latitude/Longitude como **agregação Average**, não coluna direta.
- No TMDL, `variation` numa coluna de data exige `showAsVariationsOnly` na tabela alvo —
  mais simples remover a variation.
- Em f-string de Python, `{{tag()}}` vira o literal `{tag()}` no arquivo. Isso derrubou
  o primeiro import.

### No TMDL do modelo

- **`relationship` não aceita descrição.** Um comentário `///` acima de um relacionamento
  faz o import inteiro falhar com `Property 'description' is unknown` — e a mensagem não
  diz onde está o problema. Descrição só em tabela, coluna, medida e parâmetro.
- **`sourceColumn` usa o nome depois do rename.** Se a query M faz
  `Table.RenameColumns(…, {{"motivo_original","Motivo"}})`, a coluna precisa de
  `sourceColumn: Motivo`. Com o nome antigo o modelo importa sem erro e só o **refresh**
  falha, com `column does not exist in the rowset`.

### Publicar pela API: o `definition.pbir` tem DUAS formas

O arquivo do repositório e o que vai no payload **não são o mesmo**:

| | Local (Desktop) | Publicado (API) |
|---|---|---|
| `$schema` | `definitionProperties/1.0.0` | `definitionProperties/**2.0.0**` |
| referência | `byPath` → `../<Projeto>.SemanticModel` | `byConnection` → `connectionString` |

Mandar o arquivo local direto falha com `Required properties are missing from object:
pbiServiceModelId, pbiModelVirtualServerName, …` — mensagem que sugere campos legados e
manda para o caminho errado. O que faltava era a **versão do schema**.

A connection string tem formato exato, com aspas no Data Source e minúsculas no resto:

```
Data Source="powerbi://api.powerbi.com/v1.0/myorg/<Workspace>";initial catalog=<Modelo>;integrated security=ClaimsToken;semanticmodelid=<guid>
```

> Não adivinhe: `POST /v1/workspaces/{ws}/reports/{id}/getDefinition` num relatório que
> **já funciona** devolve o gabarito exato. Foi assim que este apareceu.

### `updateDefinition` precisa do workspace no caminho

`POST /v1/semanticModels/{id}/updateDefinition` devolve **404 EntityNotFound**, como se o
modelo não existisse. O correto é `POST /v1/workspaces/{ws}/semanticModels/{id}/updateDefinition`.
Mesma regra para `reports`.

### Anotação órfã derruba o import inteiro

Remover uma coluna do TMDL com regex é fácil demais deixar para trás o bloco
`annotation SummarizationSetBy` que vinha depois dela. O import falha com:

```
TMDL objects cannot be merged because both declare the same property: value
  1st object: type=Annotation, name='SummarizationSetBy', path='./tables/fAtendimento'
```

A mensagem não diz qual coluna. A checagem é trivial e vale a pena no `validar.py`:
**número de colunas == número de anotações `SummarizationSetBy`** em cada tabela.

### Tema custom pela API não resolve o arquivo

Registrar um tema em `StaticResources/RegisteredResources/` com
`resourcePackages[].items[].path = "Hospitalar.json"` **importa sem erro e não aplica**:
o Fabric grava o item como `"path": "Hospitalar"`, sem a extensão, e o arquivo nunca é
encontrado. O relatório fica com a paleta padrão e nada avisa.

Descobre-se comparando o que você mandou com o que voltou do `getDefinition`.

Se as cores importam, **defina-as visual a visual** — que é a recomendação geral deste
roteiro de qualquer forma, porque assim o painel fica correto mesmo sem o tema.

### Treemap ignora cor por valor

`fillRule`/`linearGradient2` publica intacto no `dataPoint` do treemap e **não tem efeito
nenhum** — o visual não tem balde de saturação por medida. Para fugir da paleta categórica
(cada retângulo de um matiz, o "excesso de cores" que a aula manda evitar), fixe cor a cor
por igualdade de valor:

```json
"selector": {"data": [{"scopeId": {"Comparison": {
  "ComparisonKind": 0,
  "Left":  {"Column": {"Expression": {"SourceRef": {"Entity": "dEspecialidade"}}, "Property": "Bloco"}},
  "Right": {"Literal": {"Value": "'Clinicas'"}} }}}]}
```

Uma rampa de luminosidade no mesmo matiz mantém os retângulos distinguíveis sem virar
arco-íris. Vale para o primeiro nível do drill; os níveis abaixo voltam à paleta padrão.

### KPI estruturalmente vazio

Antes de colocar uma medida num cartão, confira se ela **pode** ter valor nesta base.
Aqui, `% Atendimentos Deficitários` saía `(Blank)` em qualquer filtro: nenhum dos 100 mil
atendimentos tem margem negativa (a menor é R$ 14,81). O DAX estava certo; o indicador é
que não existia. Mesma coisa com medidas de ranking protegidas por `HASONEVALUE` — corretas
no detalhe, `(Blank)` no cartão ao abrir a página.

Um cartão `(Blank)` parece defeito de software para quem avalia. Ou dê um valor de
fallback, ou troque por um indicador que exista.

### No relatório: o que passa na validação e mesmo assim fica ruim

Nenhuma destas quebra o import. Todas estragam a leitura, e só aparecem no PDF.

- **Matriz com colunas demais.** Medidas × categorias da coluna multiplicam: 6 medidas
  cruzadas por 3 tipos viram 18 colunas de valor em 1.232px — 65px cada, ilegível. Três
  medidas é o teto prático quando há categoria na coluna; o resto vai para a página de tabela.
- **Treemap com categorias minúsculas.** A própria aula avisa. Com dezenas de folhas, os
  retângulos do fim da cauda somem. Use drill-down em vez de despejar todos os níveis de uma vez.
- **Slicer em dropdown precisa de ~50px de altura.** Com menos, o dropdown sai cortado. A
  faixa de título que os abriga precisa de ~80px.
- **Visual composto não leva título próprio.** Quando um cartão grande, um rótulo de contexto
  e um sparkline formam um painel único, só o cartão de cima é titulado — os outros dois são
  peças, não visuais. Ensine isso ao `validar.py` (um visual sem moldura é componente), senão
  ele acusa falso positivo.
- **Sobreposição na mesma camada `z`.** Painéis compostos empilham um fundo e três visuais em
  `z` diferentes de propósito. O que nunca pode acontecer é dois visuais se sobreporem no
  **mesmo** `z` — cheque isso, é sempre erro de aritmética de layout.

### Mexer na estrutura do repositório quebra o que já está publicado

`pCaminhoCSV` guarda o caminho **dentro** do repo. Renomear o repositório é seguro (o GitHub
redireciona e os caminhos se preservam), mas **mover pastas não é**: o modelo já publicado
continua apontando para o caminho antigo e o refresh falha com "arquivo não encontrado".

Depois de reorganizar, atualize o parâmetro no modelo publicado:

```
POST /v1.0/myorg/groups/{ws}/datasets/{id}/Default.UpdateParameters
{"updateDetails":[{"name":"pCaminhoCSV","newValue":"<novo/caminho.csv>"}]}
```

E só então dispare um refresh. Alterar o `.tmdl` local não muda nada no que está no ar.

### CSV brasileiro: separador e decimal

Arquivo com `;` como separador **e vírgula decimal** precisa dos dois ajustes:

```
Csv.Document( …, [Delimiter = ";", Columns = 21, Encoding = 65001] )
Table.TransformColumnTypes( …, {…}, "pt-BR" )
```

Sem a cultura `"pt-BR"` no segundo, `1272,01` é lido como `127201` — cem vezes maior, sem
erro nenhum. O painel abre, os totais ficam absurdos, e nada no log indica o motivo.

O inverso também vale: `;` como separador **com ponto decimal** (caso do CSV de 10 mil voos)
pede cultura `"en-US"`. Olhe o arquivo antes de copiar a consulta de outro exercício —
o separador não diz qual é o decimal.

### Campo vazio no CSV vira nulo, não zero

Depois da correção de "não se aplica" (Etapa 2), o CSV tratado tem campos vazios. Na
tipagem do Power Query, texto vazio convertido para número vira `null` — e é exatamente
o que se quer: `AVERAGE` ignora, `SUM` trata como zero. Por isso a medida de atraso médio
pode ser um `AVERAGE` simples, sem filtrar cancelados à mão.

### Fonte de dados na nuvem

`File.Contents` com caminho local **não funciona** no Service. Opções, da mais simples:

1. **URL pública** (`Web.Contents` com `RelativePath`) + credencial anônima — eu configuro tudo por API
2. **OneDrive/SharePoint** (`SharePoint.Files`) — você precisa autorizar o OAuth2 na interface
3. **Dados embutidos** no código M — autossuficiente, mas pesado

### Ambiente

- Git integration **não existe** em "My workspace", tenha a capacidade que tiver
- Workspace precisa de capacidade Fabric (Trial serve); Pro sozinho não basta
- O tenant do CEUB tem **GitHub desabilitado** no Git integration (só Azure DevOps) —
  irrelevante se publicar por API
- Export PNG está bloqueado no tenant; **PDF funciona**

---

## 4. Entregáveis padrão

```
<NN>-<Exercicio>/
├── Enunciado.pdf
├── ENTREGA/                    ← o que enviar ao professor
│   ├── <Projeto>.pbix
│   └── <dados>.csv
└── projeto-powerbi/            ← repo git
    ├── <Projeto>.SemanticModel/    modelo em TMDL
    ├── <Projeto>.Report/           páginas e visuais em PBIR
    ├── dados/bruto/<dados>.csv     arquivo recebido, intocado
    ├── dados/<dados>.csv           arquivo TRATADO — fonte lida por HTTP
    ├── tratar_dados.py             audita e corrige o bruto (ver Etapa 2)
    ├── QUALIDADE-DOS-DADOS.md      erros encontrados e corrigidos (gerado)
    ├── pbir.py                     fábricas de visual (paleta, molduras, campos)
    ├── build_report.py             gera definition/pages inteiro
    ├── validar.py                  checagens da camada 1
    ├── README.md                   como publicar e republicar
    └── MAPA-DAS-PERGUNTAS.md       pergunta → visual → justificativa
```

**Gere os visuais por código, não à mão.** Um painel de 6 páginas passa de 70 arquivos
`visual.json`, cada um com 200 linhas de JSON aninhado. Escrever à mão é inviável e o diff
fica ilegível. Duas regras que fazem isso funcionar:

- **nomes determinísticos** — derive o nome do visual de um contador, não de um UUID
  aleatório. Assim reexecutar o gerador produz arquivos idênticos e o `git diff` mostra
  só o que mudou de verdade
- **uma fábrica por tipo de visual**, com a moldura (borda, fundo, título, subtítulo,
  padding) centralizada. A consistência visual sai de graça e mudar a paleta é uma linha

### O `.pbix` sai do Service, não da máquina

É um binário que só o Power BI produz — não existe caminho a partir dos arquivos-texto
do PBIP. Mas **publicar destrava o export**, e aí não precisa de Desktop nem de Windows:

```
GET /v1.0/myorg/groups/{ws}/reports/{id}/Export
```

Funciona mesmo quando o botão da interface está cinza, e o arquivo vem com o `DataModel`
embutido — abre sozinho, sem depender do Fabric. Confira com
`zipfile.ZipFile(p).namelist()`: tem que aparecer `DataModel`.

Ou seja: a ordem é **publicar → validar → exportar o `.pbix`**, nunca o contrário. E se
o painel mudar depois, o `.pbix` precisa ser exportado de novo — ele é um retrato, não um
link.

A rota do Desktop (duplo clique no `.pbip`, **Arquivo → Salvar como → .pbix**) continua
valendo quando não há workspace.

Para baixar o `.pbix` pronto do Service (funciona mesmo quando o botão da interface está cinza):

```
GET /v1.0/myorg/groups/{ws}/reports/{id}/Export
```

---

## 5. Quando o Power BI não é a melhor escolha

Se o enunciado não exigir Power BI, um **HTML único com os dados embutidos** costuma ser
melhor: abre com duplo clique, não depende de licença, de nuvem nem de refresh, e roda em
qualquer máquina. Foi a primeira entrega do exercício hospitalar
(`01-Hospitalar/dashboard-hospitalar.html`), com os cinco gráficos tradicionais do enunciado.

O mesmo exercício ganhou depois uma versão Power BI (`01-Hospitalar/projeto-powerbi/`) com os
cinco visuais **especializados** da aula 05 — cartões/KPIs, treemap, mapa, matriz e tabela.
Os dois convivem: o HTML entrega sem dependência, o PBIP entrega o modelo semântico e o
drill-down que o HTML não tem.

Diga qual dos dois você quer — ou me deixe recomendar depois de ler o enunciado.
