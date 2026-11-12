#!/usr/bin/env python3
"""
AINDA NÃO IMPLEMENTADO.

Vai sincronizar data/ferias.json a partir do quadro Trello "PLANO DE FÉRIAS
2.0". Falta descobrir a estrutura real do quadro (uma lista por militar? uma
lista por mês? datas em campos personalizados, no título do card ou na
descrição?) antes de escrever o parser -- igual foi feito com o Google Docs
em scripts/sync_escala.py, adivinhar o formato sem ver o quadro real geraria
um parser errado.

Quando o quadro estiver acessível (conector do Trello conectado, ou link
público), este script deve:
  1. Buscar os cards do quadro (via conector MCP do Trello nesta sessão, ou
     via REST com TRELLO_KEY/TRELLO_TOKEN se formos automatizar pelo GitHub
     Actions no futuro).
  2. Extrair, para cada militar de férias: nome, posto, data de início e
     data de fim do período.
  3. Gravar data/ferias.json neste formato:
       {
         "atualizadoEm": "2026-11-12T00:00:00Z",
         "linkQuadro": "https://trello.com/b/XXXXXXXX",
         "periodos": [
           {"nome": "TEN CEL FULANA DE TAL", "posto": "TEN CEL",
            "inicio": "01/12/2026", "fim": "15/12/2026"}
         ]
       }
     (scripts/sync_escala.py já lê esse arquivo e remove automaticamente
     quem estiver de férias das demais escalas, registrando o conflito na
     auditoria.)
"""
import sys

if __name__ == "__main__":
    print(__doc__, file=sys.stderr)
    sys.exit(1)
