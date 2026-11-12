# Escalas — 1ª Policlínica (CBMERJ)

Site público com as escalas de serviço da 1ª Policlínica do CBMERJ (Campinho):
Assistencial, Oficial de Dia, SPA, Permanência, Administrativo, Enfermagem e
Férias. Tem ainda duas páginas de apoio: **Correções do dia** (faltas,
substituições e permutas) e **Auditoria** (inconsistências encontradas
automaticamente).

**Site:** publicado via GitHub Pages a partir deste repositório (`index.html` na raiz).

## Como funciona

A administração **não edita nada neste repositório**. As fontes de dados são:

| Dado | Fonte | Quem edita |
|---|---|---|
| Escala mensal (6 tipos) | Google Docs | Administração, como sempre |
| Férias | Quadro Trello "PLANO DE FÉRIAS 2.0" | Administração, como sempre |
| Correções do dia (falta/substituição/permuta) | Planilha Google Sheets "Correções Diárias" | Administração |
| Contatos/WhatsApp | `data/contatos.json` neste repositório | Administração, direto no GitHub |

Todas essas fontes precisam continuar compartilhadas como **"Qualquer pessoa
com o link pode visualizar"** — é assim que os scripts leem sem precisar de
senha/API key.

Um workflow do GitHub Actions (`.github/workflows/sync-escala.yml`) roda:

- automaticamente **a cada hora**, e
- manualmente quando alguém clicar em **Actions → Sincronizar escala (Google
  Docs) → Run workflow**, ou no botão "Forçar sincronização" no rodapé do
  site (leva direto para essa tela do GitHub).

Ele baixa o Google Docs, converte as tabelas em `data/escalas.json`, remove
quem estiver de férias (ver abaixo), roda a auditoria e publica tudo
automaticamente (commit direto na branch). O botão **"🔄 Atualizar dados"**
no site é diferente: ele só recarrega, no navegador de quem clicar, os dados
já publicados (sem nenhuma credencial) — não dispara a sincronização de
verdade, por segurança (ver "Por que o botão de atualizar não sincroniza
direto" mais abaixo).

Se o documento tiver algum problema de formatação que impeça o parser de
reconhecer as 6 escalas, o workflow **falha sem alterar nada** — o site
continua mostrando os últimos dados válidos até o documento ser corrigido.

### Férias (`data/ferias.json`) — ⚠️ pendente

A integração com o Trello ainda não está pronta: falta ver a estrutura real
do quadro "PLANO DE FÉRIAS 2.0" para escrever o parser (`scripts/sync_ferias.py`
hoje é só um esqueleto). Até lá, `data/ferias.json` fica com `periodos: []`
e o chip "Férias" do site mostra "nenhum período sincronizado ainda".

Quando alguém estiver de férias e `data/ferias.json` tiver o período dessa
pessoa, `scripts/sync_escala.py` **remove automaticamente** essa pessoa de
qualquer escala em que ainda apareça lançada nas datas do período, e registra
cada remoção como um achado de auditoria (severidade alta) — assim a
administração sabe que precisa corrigir o Google Docs.

### Correções do dia (`data/correcoes.json`)

Planilha Google Sheets própria (não é o mesmo documento da escala mensal),
criada para lançar falta/substituição/permuta sem precisar reabrir a escala
inteira. Colunas, nesta ordem: Data, Escala, Tipo (Falta/Substituição/Permuta),
Profissional original, Profissional substituto/novo, Observação.
`scripts/sync_correcoes.py` lê essa planilha e gera `data/correcoes.json`,
exibido na página `correcoes.html`.

### Auditoria (`data/auditoria.json`)

Gerada junto com a escala (dentro de `scripts/sync_escala.py`, lógica em
`scripts/auditoria.py`). Verifica:

- **Conflito com férias** — pessoa de férias ainda lançada em alguma escala.
- **Dia sem profissional** — um dia da escala ficou sem ninguém.
- **Lacuna de cobertura 24h** — Oficial de Dia e Permanência precisam cobrir
  todo santo dia do mês; qualquer data faltando é sinalizada.
- **Possível nome duplicado** — dois nomes muito parecidos nas escalas
  (provável erro de digitação criando duas "pessoas" para o mesmo militar).

Exibida em `auditoria.html`, com um contador vermelho na navegação sempre que
houver achados de severidade alta.

### Por que o botão de atualizar não sincroniza direto

O site é 100% estático (GitHub Pages, sem servidor). Um botão que de fato
buscasse o Google Docs/Sheets/Trello e commitasse no repositório precisaria de
credenciais com permissão de escrita — colocar isso no JavaScript de uma
página pública deixaria essas credenciais acessíveis a qualquer visitante.
Por isso o chip do site só recarrega o que já foi publicado, e a
sincronização de verdade continua restrita ao GitHub Actions (agendado ou
disparado manualmente por alguém com acesso ao repositório).

## Contatos / WhatsApp (`data/contatos.json`)

Cada militar que aparece em alguma escala ganha uma linha neste arquivo
(posto, nome e um campo `whatsapp` vazio). Quando a administração preenche o
campo `whatsapp` (formato internacional, só números — ex: `5521999998888`),
um botão de WhatsApp passa a aparecer ao lado do nome da pessoa no site
(inclusive na página de Férias).

**Atenção:** este repositório é **público** — qualquer telefone colocado em
`data/contatos.json` fica publicamente visível (inclusive no histórico do
Git). Preencha apenas números que podem ficar públicos.

A sincronização automática **acrescenta** militares novos que aparecerem na
escala (com telefone em branco) mas **nunca apaga ou sobrescreve** um
telefone já preenchido manualmente.

## Estrutura

```
index.html                       escalas (Geral, Assistencial, ..., Férias)
correcoes.html                    página "Correções do dia"
auditoria.html                    página "Auditoria"
assets/site.css                   design system compartilhado pelas 3 páginas
data/escalas.json                 escala do mês, gerada automaticamente
data/ferias.json                  períodos de férias (Trello — pendente)
data/correcoes.json               faltas/substituições/permutas do dia a dia
data/auditoria.json               achados da auditoria automática
data/contatos.json                nome/posto/whatsapp, editado manualmente
scripts/sync_escala.py            Google Docs → escalas.json (+ exclusão de férias + auditoria)
scripts/sync_correcoes.py         Google Sheets → correcoes.json
scripts/sync_ferias.py            Trello → ferias.json (ainda não implementado)
scripts/auditoria.py              regras de verificação usadas por sync_escala.py
.github/workflows/sync-escala.yml agendamento + atualização automática
```

## Publicar o site (passo único, manual)

No GitHub: **Settings → Pages → Build and deployment → Source: "Deploy from a
branch"** → branch `main`, pasta `/ (root)`.

## Rodar/testar localmente

```bash
python3 scripts/sync_escala.py <DOC_ID>               # Google Docs → data/escalas.json + auditoria
python3 scripts/sync_correcoes.py <SPREADSHEET_ID>    # Google Sheets → data/correcoes.json
python3 -m http.server 8000                           # serve a pasta atual
# abrir http://localhost:8000/
```
