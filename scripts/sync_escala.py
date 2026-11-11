#!/usr/bin/env python3
"""
Sincroniza as escalas de servico da 1a Policlinica a partir do Google Docs
mantido pela administracao, convertendo o documento (compartilhado como
"qualquer pessoa com o link pode visualizar") em data/escalas.json, que o
site estatico consome.

Tambem mantem data/contatos.json: adiciona militares novos encontrados na
escala (telefone em branco), sem nunca sobrescrever um telefone ja
cadastrado pela administracao.

Uso:
    python3 scripts/sync_escala.py <DOC_ID>

O DOC_ID e o trecho entre /d/ e /edit no link do Google Docs, por exemplo:
    https://docs.google.com/document/d/1DfpvDzd5cr31Xlbeb-xU32j6uXgPFpc2ZV7dRN1sYqM/edit
                                        \\_______________ DOC_ID ______________/
"""
import json
import os
import re
import sys
import unicodedata
import urllib.request
from collections import Counter
from datetime import date, datetime, timezone

WEEKDAYS_PT = [
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
]
MONTHS_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

# Secoes reconhecidas no documento. Qualquer outro "# Titulo" encontrado no
# documento (ex: rascunhos, secoes descontinuadas) e ignorado silenciosamente
# -- so o que estiver nesta lista entra no site.
SECTIONS = {
    "ASSISTENCIAL": {"id": "assistencial", "label": "Assistencial", "layout": "shift", "cols_total": 4, "unit": "turnos"},
    "OFICIAL DE DIA": {"id": "oficial", "label": "Oficial de Dia", "layout": "pair", "cols_total": 3, "unit": "designações", "cols": ["Oficial de Dia", "Sobreaviso"]},
    "SPA": {"id": "spa", "label": "SPA", "short": "Serviço de Pronto Atendimento (SPA)", "layout": "shift", "cols_total": 4, "unit": "turnos"},
    "PERMANÊNCIA": {"id": "permanencia", "label": "Permanência", "layout": "pair", "cols_total": 3, "unit": "designações", "cols": ["Permanência", "Sobreaviso"]},
    "ADMINISTRATIVO": {"id": "administrativo", "label": "Administrativo", "layout": "team", "cols_total": 3, "unit": "presenças"},
    "ENFERMAGEM": {"id": "enfermagem", "label": "Enfermagem", "layout": "team", "cols_total": 3, "unit": "presenças"},
}

RANK_PATTERNS = [
    r'^TEN\s+CEL\b',
    r'^SUBTEN\b',
    r'^[1-3][°º]\s*TEN\b',
    r'^[1-3][°º]\s*SGT\b',
    r'^CEL\b',
    r'^MAJ\b',
    r'^CAP\b',
    r'^SGT\b',
    r'^TEN\b',
]

DATE_RE = re.compile(r'^(\d{2}/\d{2}/\d{4})\s*-{1,2}\s*(.*)$')
TIME_RANGE_RE = re.compile(r'^(\d{1,2}h\s*[-–]\s*\d{1,2}h)\s*(.*)$', re.IGNORECASE)
RG_RE = re.compile(r',?\s*RG:?\s*[\d.]+\s*\.?\s*$', re.IGNORECASE)
ALIGN_ROW_RE = re.compile(r'^\|\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$')
HEADING_RE = re.compile(r'^#\s+(.+?)\s*\*{0,2}\s*$')


def clean_text(t):
    t = t.replace('\\*\\*', '').replace('**', '').replace('\\', '')
    return re.sub(r'\s+', ' ', t).strip()


def strip_rg(t):
    return RG_RE.sub('', t).strip().rstrip(',').strip()


def weekday_pt(dd, mm, yy):
    return WEEKDAYS_PT[date(yy, mm, dd).weekday()]


def split_rank(name):
    n = re.sub(r'\s+', ' ', name).strip()
    for pat in RANK_PATTERNS:
        m = re.match(pat, n, re.IGNORECASE)
        if m:
            return m.group(0).strip().upper(), n[m.end():].strip()
    return '', n


def norm_key(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s).strip().upper()


def split_row(line, expected_cols):
    raw = line.strip()
    if not raw.startswith('|'):
        return None
    parts = raw.split('|')[1:-1]
    cells = [clean_text(p) for p in parts]
    if len(cells) < expected_cols:
        cells = cells + [''] * (expected_cols - len(cells))
    elif len(cells) > expected_cols:
        cells = cells[:expected_cols]
    return cells


def is_feriado(cell):
    return 'FERIADO' in cell.upper()


def parse_doc(text):
    sections_out = []
    cur_cfg = cur_days = cur_day = None
    expect_cols = None
    seen_title_row = seen_header_row = False

    def flush_day():
        nonlocal cur_day
        if cur_day is not None and cur_days is not None:
            cur_days.append(cur_day)
        cur_day = None

    for raw_line in text.split('\n'):
        line = raw_line.rstrip('\n')
        heading = HEADING_RE.match(line.strip())
        if heading:
            flush_day()
            name = clean_text(heading.group(1)).upper()
            if name in SECTIONS:
                cur_cfg = SECTIONS[name]
                cur_days = []
                sections_out.append((cur_cfg, cur_days))
                expect_cols = cur_cfg["cols_total"]
                seen_title_row = seen_header_row = False
            else:
                cur_cfg = None
                cur_days = None
            continue

        if cur_cfg is None or not line.strip().startswith('|'):
            continue
        if ALIGN_ROW_RE.match(line.strip()):
            continue

        cells = split_row(line, expect_cols)
        if cells is None:
            continue
        if not seen_title_row:
            seen_title_row = True
            continue
        if not seen_header_row:
            seen_header_row = True
            continue

        need = 3 if cur_cfg["layout"] == "shift" else (1 if cur_cfg["layout"] == "team" else 2)
        first = cells[0]
        m = DATE_RE.match(first)
        if m:
            flush_day()
            dd, mm, yy = (int(x) for x in m.group(1).split('/'))
            cur_day = {"d": m.group(1), "wd": weekday_pt(dd, mm, yy)}
            if cur_cfg["layout"] == "shift":
                cur_day["r"] = []
            elif cur_cfg["layout"] == "team":
                cur_day["t"] = []
            else:
                cur_day["a"], cur_day["b"] = [], []
            fields = cells[1:1 + need]
        else:
            if cur_day is None:
                continue
            # linha bem formada: cells[0] e o espaco (vazio) da celula de data
            # mesclada. Linha malformada: a celula de data foi removida do
            # texto exportado e o conteudo real comeca ja em cells[0].
            fields = cells[1:1 + need] if cells[0].strip() == '' else cells[0:need]

        if cur_cfg["layout"] == "shift":
            name_cell, m_cell, t_cell = (fields + ['', '', ''])[:3]
            if is_feriado(name_cell):
                cur_day["feriado"] = strip_rg(name_cell)
                continue
            if not name_cell.strip():
                continue
            s = (1 if m_cell.strip().upper() == 'X' else 0) | (2 if t_cell.strip().upper() == 'X' else 0)
            if s:
                cur_day["r"].append([strip_rg(name_cell), s])
        elif cur_cfg["layout"] == "team":
            name_cell = (fields + [''])[0]
            if is_feriado(name_cell):
                cur_day["feriado"] = strip_rg(name_cell)
                continue
            if name_cell.strip():
                cur_day["t"].append(strip_rg(name_cell))
        else:
            a_cell, b_cell = (fields + ['', ''])[:2]
            tm = TIME_RANGE_RE.match(a_cell.strip())
            if tm:
                cur_day["a"].append({"n": strip_rg(tm.group(2)), "t": tm.group(1).replace(' ', '')})
            elif a_cell.strip():
                cur_day["a"].append({"n": strip_rg(a_cell)})
            tm2 = TIME_RANGE_RE.match(b_cell.strip())
            if tm2:
                cur_day["b"].append({"n": strip_rg(tm2.group(2)), "t": tm2.group(1).replace(' ', '')})
            elif b_cell.strip():
                cur_day["b"].append({"n": strip_rg(b_cell)})

    flush_day()
    return sections_out


def dia_names(cfg, day):
    if cfg["layout"] == "shift":
        return [n for n, _ in day.get("r", [])]
    if cfg["layout"] == "team":
        return list(day.get("t", []))
    return [e["n"] for e in day.get("a", [])] + [e["n"] for e in day.get("b", [])]


def fetch_doc_text(doc_id):
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="replace")


def build_escalas_json(sections, doc_id):
    month_counts = Counter()
    out_sections = []
    for cfg, days in sections:
        entry = dict(cfg)
        entry["days"] = days
        out_sections.append(entry)
        for d in days:
            dd, mm, yy = (int(x) for x in d["d"].split('/'))
            month_counts[(mm, yy)] += 1

    competencia = None
    if month_counts:
        (mm, yy), _ = month_counts.most_common(1)[0]
        competencia = f"{MONTHS_PT[mm - 1]}/{yy}"

    return {
        "competencia": competencia,
        "atualizadoEm": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "docId": doc_id,
        "linkEdicao": f"https://docs.google.com/document/d/{doc_id}/edit",
        "escalas": out_sections,
    }


def merge_contatos(sections, path):
    existing = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            existing = json.load(f)
    by_key = {norm_key(c["nome"]): c for c in existing}

    for cfg, days in sections:
        for day in days:
            for raw in dia_names(cfg, day):
                posto, nome = split_rank(raw)
                key = norm_key(nome)
                if key not in by_key:
                    novo = {
                        "id": key.replace(' ', '_').lower(),
                        "posto": posto,
                        "nome": nome,
                        "whatsapp": "",
                    }
                    by_key[key] = novo
                    existing.append(novo)

    existing.sort(key=lambda c: c["nome"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/sync_escala.py <DOC_ID> [caminho_txt_local]", file=sys.stderr)
        sys.exit(1)
    doc_id = sys.argv[1]

    if len(sys.argv) >= 3:
        with open(sys.argv[2], encoding="utf-8") as f:
            text = f.read()
    else:
        text = fetch_doc_text(doc_id)

    sections = parse_doc(text)

    missing = [cfg["label"] for cfg, days in sections if not days]
    found_ids = {cfg["id"] for cfg, _ in sections}
    absent = [cfg["label"] for cfg in SECTIONS.values() if cfg["id"] not in found_ids]
    if absent or missing:
        print(f"ERRO: não foi possível reconhecer corretamente o documento.", file=sys.stderr)
        if absent:
            print(f"  Seções não encontradas: {', '.join(absent)}", file=sys.stderr)
        if missing:
            print(f"  Seções encontradas sem nenhum dia: {', '.join(missing)}", file=sys.stderr)
        print("  Nada foi escrito -- o site continua com os últimos dados válidos.", file=sys.stderr)
        sys.exit(2)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(repo_root, "data")
    os.makedirs(data_dir, exist_ok=True)

    escalas = build_escalas_json(sections, doc_id)
    with open(os.path.join(data_dir, "escalas.json"), "w", encoding="utf-8") as f:
        json.dump(escalas, f, ensure_ascii=False, indent=2)
        f.write("\n")

    merge_contatos(sections, os.path.join(data_dir, "contatos.json"))

    total_dias = sum(len(d) for _, d in sections)
    print(f"OK: {escalas['competencia']} — {len(sections)} escalas, {total_dias} dias no total.")


if __name__ == "__main__":
    main()
