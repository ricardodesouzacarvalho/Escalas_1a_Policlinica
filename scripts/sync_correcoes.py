#!/usr/bin/env python3
"""
Sincroniza data/correcoes.json a partir da planilha Google Sheets
"Correções Diárias" mantida pela administração (faltas, substituições e
permutas do dia a dia, separado da escala mensal do Google Docs).

A planilha precisa estar compartilhada como "qualquer pessoa com o link
pode visualizar" (Arquivo > Compartilhar), com colunas, nesta ordem:
    Data (DD/MM/AAAA) | Escala | Tipo | Profissional original |
    Profissional substituto/novo | Observação

Uso:
    python3 scripts/sync_correcoes.py <SPREADSHEET_ID> [--gid 0]
"""
import argparse
import csv
import io
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')


def fetch_csv(spreadsheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    return raw.decode("utf-8-sig", errors="replace")


def parse_csv(text):
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    correcoes = []
    for row in rows[1:]:  # pula o cabeçalho
        row = (row + [""] * 6)[:6]
        data, escala, tipo, original, novo, obs = (c.strip() for c in row)
        if "EXEMPLO" in obs.upper():
            continue
        if not DATE_RE.match(data) or not original:
            continue
        correcoes.append({
            "data": data,
            "escala": escala,
            "tipo": tipo,
            "profissionalOriginal": original,
            "profissionalNovo": novo,
            "observacao": obs,
        })

    def chave_data(c):
        d, m, y = c["data"].split('/')
        return (y, m, d)

    correcoes.sort(key=chave_data, reverse=True)
    return correcoes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spreadsheet_id")
    ap.add_argument("--gid", default="0")
    args = ap.parse_args()

    text = fetch_csv(args.spreadsheet_id, args.gid)
    correcoes = parse_csv(text)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = {
        "atualizadoEm": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "linkPlanilha": f"https://docs.google.com/spreadsheets/d/{args.spreadsheet_id}/edit",
        "correcoes": correcoes,
    }
    with open(os.path.join(repo_root, "data", "correcoes.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"OK: {len(correcoes)} correção(ões) lida(s).")


if __name__ == "__main__":
    main()
