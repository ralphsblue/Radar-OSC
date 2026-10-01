"""Baixa a relacao de licitantes inidoneos do TCU pela API REST publica (Oracle ORDS).

Endpoint descoberto na fase 0 (sem chave, sem CAPTCHA):
  GET https://contas.tcu.gov.br/ords/condenacao/consulta/inidoneos[?offset=N&limit=M]
Resposta: {"items": [...], "hasMore": bool, "limit": 25, "offset": 0, "count": n, "links": [...]}
Item: nome, cpf_cnpj (formatado com pontuacao), processo, deliberacao, data_transito_julgado,
      data_final, data_acordao, uf, municipio (datas ISO 8601 em UTC).

Tambem testa o filtro ORDS q={"cpf_cnpj":"..."} e salva exemplos.
Uso: PYTHONIOENCODING=utf-8 .venv/Scripts/python fase0/portal/tcu_inidoneos.py
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
URL = "https://contas.tcu.gov.br/ords/condenacao/consulta/inidoneos"
PASTA = Path(__file__).parent / "tcu"
PAUSA = 1.5


def main() -> None:
    PASTA.mkdir(exist_ok=True)
    itens: list[dict] = []
    tempos = []
    with httpx.Client(headers={"User-Agent": UA}, timeout=60) as c:
        offset = 0
        limite = 100
        while True:
            t0 = time.perf_counter()
            r = c.get(URL, params={"offset": offset, "limit": limite})
            tempos.append(time.perf_counter() - t0)
            r.raise_for_status()
            d = r.json()
            if offset == 0:
                print("limit efetivo pedido=100 ->", d.get("limit"), "count", d.get("count"))
            itens.extend(d["items"])
            if not d.get("hasMore"):
                break
            offset += d["count"]
            time.sleep(PAUSA)

        (PASTA / "inidoneos_completo.json").write_text(json.dumps(itens, ensure_ascii=False, indent=1), encoding="utf-8")
        agora = datetime.now(timezone.utc)
        pj = [i for i in itens if len("".join(ch for ch in i["cpf_cnpj"] or "" if ch.isdigit())) == 14]
        vig = [i for i in pj if not i["data_final"] or datetime.fromisoformat(i["data_final"].replace("Z", "+00:00")) >= agora]
        print(f"total {len(itens)} | PJ {len(pj)} | PJ vigentes {len(vig)} | tempo medio {sum(tempos)/len(tempos):.2f}s")
        print("formatos de cpf_cnpj:", sorted({len(i['cpf_cnpj'] or '') for i in itens}))
        for i in vig[:8]:
            print("  ", i["cpf_cnpj"], "|", i["nome"], "|", i["processo"], "|", i["deliberacao"], "|", i["data_transito_julgado"], "->", i["data_final"], "|", i["uf"])

        # Teste de filtro ORDS (q=JSON). Formatado e so digitos.
        if vig:
            alvo = vig[0]["cpf_cnpj"]
            for valor in (alvo, "".join(ch for ch in alvo if ch.isdigit())):
                time.sleep(PAUSA)
                r = c.get(URL, params={"q": json.dumps({"cpf_cnpj": valor})})
                print("filtro q cpf_cnpj=", valor, "->", r.status_code, "itens:", len(r.json().get("items", [])) if r.headers.get("content-type", "").startswith("application/json") else r.text[:200])
                (PASTA / f"exemplo_filtro_{'fmt' if '.' in valor else 'digitos'}.json").write_text(r.text, encoding="utf-8")
            time.sleep(PAUSA)
            r = c.get(URL, params={"q": json.dumps({"cpf_cnpj": "19.131.243/0001-97"})})
            print("filtro nada consta ->", r.status_code, r.text[:300])
            (PASTA / "exemplo_nada_consta.json").write_text(r.text, encoding="utf-8")
        time.sleep(PAUSA)
        r = c.get("https://contas.tcu.gov.br/ords/condenacao/metadata-catalog/consulta/item")
        print("metadata-catalog ->", r.status_code, r.text[:500])
        (PASTA / "metadata_catalog.json").write_text(r.text, encoding="utf-8")


if __name__ == "__main__":
    main()
