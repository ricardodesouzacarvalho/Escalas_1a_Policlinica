#!/usr/bin/env python3
"""
Roda verificações automáticas sobre data/escalas.json (e, quando existirem,
data/ferias.json e data/correcoes.json) e gera data/auditoria.json com os
achados, para a página auditoria.html do site.

Verificações:
  - conflito_ferias: pessoa estava de férias (Trello) e foi removida de uma
    escala em que ainda aparecia lançada no Google Docs (lista repassada por
    quem chama run_audit, normalmente scripts/sync_escala.py).
  - dia_sem_profissional: um dia existe na escala mas ficou sem ninguém
    lançado (ex: todos os lançamentos daquele dia foram removidos).
  - lacuna_cobertura: em escalas de cobertura 24h (Oficial de Dia,
    Permanência), falta uma data do mês -- elas devem cobrir todo santo dia.
  - nome_parecido: dois nomes distintos nas escalas são grafados de forma
    muito parecida (possível erro de digitação gerando duas "pessoas"
    diferentes para o mesmo militar).

Uso:
    python3 scripts/auditoria.py                # lê e grava em data/
    python3 scripts/auditoria.py --escalas X.json --out Y.json
"""
import argparse
import calendar
import difflib
import json
import os
import re
import unicodedata
from datetime import datetime, timezone

# Escalas de cobertura 24h: devem ter uma entrada para cada dia do mês, sem
# nenhuma lacuna.
COBERTURA_24H = {"oficial", "permanencia"}


def norm_key(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s).strip().upper()


def dia_names(sc, day):
    if sc["layout"] == "shift":
        return [n for n, _ in day.get("r", [])]
    if sc["layout"] == "team":
        return list(day.get("t", []))
    return [e["n"] for e in day.get("a", [])] + [e["n"] for e in day.get("b", [])]


def dia_vazio(sc, day):
    if "feriado" in day:
        return False
    if sc["layout"] == "shift":
        return len(day.get("r", [])) == 0
    if sc["layout"] == "team":
        return len(day.get("t", [])) == 0
    return len(day.get("a", [])) == 0 and len(day.get("b", [])) == 0


def checar_lacunas(sc):
    achados = []
    datas = set()
    anos_meses = set()
    for day in sc["days"]:
        dd, mm, yy = (int(x) for x in day["d"].split('/'))
        datas.add((dd, mm, yy))
        anos_meses.add((mm, yy))
    for mm, yy in anos_meses:
        _, ultimo_dia = calendar.monthrange(yy, mm)
        for dd in range(1, ultimo_dia + 1):
            if (dd, mm, yy) not in datas:
                achados.append({
                    "severidade": "media",
                    "tipo": "lacuna_cobertura",
                    "escalaId": sc["id"],
                    "data": f"{dd:02d}/{mm:02d}/{yy}",
                    "descricao": f"{sc['label']} é escala de cobertura 24h e não tem ninguém lançado em {dd:02d}/{mm:02d}/{yy}.",
                })
    return achados


def checar_dias_vazios(sc):
    achados = []
    for day in sc["days"]:
        if dia_vazio(sc, day):
            achados.append({
                "severidade": "alta",
                "tipo": "dia_sem_profissional",
                "escalaId": sc["id"],
                "data": day["d"],
                "descricao": f"{sc['label']}: {day['d']} ({day['wd']}) está sem nenhum profissional lançado.",
            })
    return achados


def checar_nomes_parecidos(escalas):
    nomes = set()
    for sc in escalas:
        for day in sc["days"]:
            for n in dia_names(sc, day):
                nomes.add(norm_key(n))
    nomes = sorted(nomes)
    achados = []
    vistos = set()
    for i, a in enumerate(nomes):
        for b in nomes[i + 1:]:
            if a == b:
                continue
            par = tuple(sorted((a, b)))
            if par in vistos:
                continue
            ratio = difflib.SequenceMatcher(None, a, b).ratio()
            if ratio >= 0.90 and abs(len(a) - len(b)) <= 3:
                vistos.add(par)
                achados.append({
                    "severidade": "baixa",
                    "tipo": "nome_parecido",
                    "escalaId": None,
                    "data": None,
                    "descricao": f'Nomes parecidos podem ser a mesma pessoa grafada diferente: "{a}" e "{b}".',
                })
    return achados


def checar_conflitos_ferias(conflitos_ferias):
    achados = []
    for c in conflitos_ferias or []:
        achados.append({
            "severidade": "alta",
            "tipo": "conflito_ferias",
            "escalaId": c.get("escalaId"),
            "data": c.get("data"),
            "descricao": (
                f'{c.get("nome")} estava de férias (Trello) e foi removido(a) da escala '
                f'{c.get("escalaLabel", c.get("escalaId"))} em {c.get("data")}, onde ainda '
                f'aparecia lançado(a) no Google Docs.'
            ),
        })
    return achados


def run_audit(escalas, conflitos_ferias=None):
    achados = []
    for sc in escalas:
        achados.extend(checar_dias_vazios(sc))
        if sc["id"] in COBERTURA_24H:
            achados.extend(checar_lacunas(sc))
    achados.extend(checar_nomes_parecidos(escalas))
    achados.extend(checar_conflitos_ferias(conflitos_ferias))

    ordem_sev = {"alta": 0, "media": 1, "baixa": 2}
    achados.sort(key=lambda a: (ordem_sev.get(a["severidade"], 9), a.get("data") or ""))

    resumo = {"alta": 0, "media": 0, "baixa": 0}
    for a in achados:
        resumo[a["severidade"]] = resumo.get(a["severidade"], 0) + 1

    return {
        "geradoEm": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "resumo": resumo,
        "achados": achados,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--escalas", default=None, help="Caminho para escalas.json (default: data/escalas.json)")
    ap.add_argument("--out", default=None, help="Caminho de saída (default: data/auditoria.json)")
    args = ap.parse_args()

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    escalas_path = args.escalas or os.path.join(repo_root, "data", "escalas.json")
    out_path = args.out or os.path.join(repo_root, "data", "auditoria.json")

    with open(escalas_path, encoding="utf-8") as f:
        data = json.load(f)

    resultado = run_audit(data["escalas"])
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
        f.write("\n")

    r = resultado["resumo"]
    print(f"OK: {len(resultado['achados'])} achados (alta={r['alta']}, média={r['media']}, baixa={r['baixa']})")


if __name__ == "__main__":
    main()
