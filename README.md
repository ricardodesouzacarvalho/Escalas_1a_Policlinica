# Escalas — 1ª Policlínica (CBMERJ)

Site público com as escalas de serviço da 1ª Policlínica do CBMERJ (Campinho):
Assistencial, Oficial de Dia, SPA, Permanência, Administrativo e Enfermagem.

**Site:** publicado via GitHub Pages a partir deste repositório (`index.html` na raiz).

## Como funciona

A administração **não edita nada neste repositório**. A escala de cada mês é
feita normalmente em um **Google Docs** (o mesmo documento de sempre, com uma
tabela por tipo de escala). Esse documento precisa continuar compartilhado
como **"Qualquer pessoa com o link pode visualizar"**.

Um workflow do GitHub Actions (`.github/workflows/sync-escala.yml`) roda:

- automaticamente **a cada hora**, e
- manualmente quando alguém clicar em **Actions → Sincronizar escala (Google
  Docs) → Run workflow** (útil para atualizar na hora, sem esperar a próxima
  rodada agendada).

Ele baixa o texto do Google Docs, converte as tabelas em `data/escalas.json` e
publica automaticamente (commit direto na branch). O site estático
(`index.html`) lê esse JSON a cada carregamento de página — não há nenhum
passo de build.

Se o documento tiver algum problema de formatação que impeça o parser de
reconhecer as 6 escalas, o workflow **falha sem alterar nada** — o site
continua mostrando os últimos dados válidos até o documento ser corrigido.

### Link de edição no site

O rodapé/topo do site mostra "Editar escala do mês no Google Docs", apontando
sempre para o mesmo documento. Quem tiver permissão de edição no Doc entra
direto por ali.

## Contatos / WhatsApp (`data/contatos.json`)

Cada militar que aparece em alguma escala ganha uma linha neste arquivo
(posto, nome e um campo `whatsapp` vazio). Quando a administração preenche o
campo `whatsapp` (formato internacional, só números — ex: `5521999998888`),
um botão de WhatsApp passa a aparecer ao lado do nome da pessoa no site.

**Atenção:** este repositório é **público** — qualquer telefone colocado em
`data/contatos.json` fica publicamente visível (inclusive no histórico do
Git). Preencha apenas números que podem ficar públicos.

A sincronização automática **acrescenta** militares novos que aparecerem na
escala (com telefone em branco) mas **nunca apaga ou sobrescreve** um
telefone já preenchido manualmente.

## Estrutura

```
index.html                       site (HTML/CSS/JS puro, sem build)
data/escalas.json                dados do mês, gerados automaticamente
data/contatos.json               nome/posto/whatsapp, editado manualmente
scripts/sync_escala.py           parser Google Docs → escalas.json
.github/workflows/sync-escala.yml   agendamento + atualização automática
```

## Publicar o site (passo único, manual)

No GitHub: **Settings → Pages → Build and deployment → Source: "Deploy from a
branch"** → branch `main`, pasta `/ (root)`.

## Rodar/testar localmente

```bash
python3 scripts/sync_escala.py <DOC_ID>   # busca o Google Docs e atualiza data/
python3 -m http.server 8000               # serve a pasta atual
# abrir http://localhost:8000/
```
