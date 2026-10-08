"""Baixa as listas de responsáveis (pessoa física) da Plataforma de Certidões do TCU.

Endpoints oficiais documentados em https://sites.tcu.gov.br/dados-abertos/webservices-tcu/
(POST com filtro opcional no corpo; corpo {} devolve a lista inteira):

- responsaveis-contas-irregulares (CADIRREG, contas julgadas irregulares, transitado em julgado)
- responsaveis-fins-eleitorais (irregulares com débito, últimos 8 anos; exige anoEleicao)
- responsaveis-inabilitados (inabilitados para cargo em comissão ou função de confiança)

Também baixa o CSV de exportação usado pelo frontend, para comparar.
Sem CAPTCHA nesses endpoints. Pausa de 2 s entre chamadas.

Saída (fora do versionamento, contém CPF completo): downloads/tcu_<lista>.json e .csv,
mais downloads/tcu_meta.json com status, tempo, tamanho e data.

Uso: .venv/Scripts/python fase0/dirigentes/baixar_tcu_listas.py
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime

from comum import DOWNLOADS, cliente, esperar

BASE = "https://certidoes.apps.tcu.gov.br/api/publico"
LISTAS = [
    "responsaveis-contas-irregulares",
    "responsaveis-inabilitados",
    "responsaveis-fins-eleitorais",
]


def main() -> None:
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    meta: dict = {"data_utc": datetime.now(UTC).isoformat(), "chamadas": []}
    with cliente() as c:
        esperar()
        r = c.get(f"{BASE}/eleicoes/ultimoAno")
        ano = str(r.json()["ano"])
        esperar()
        anos = c.get(f"{BASE}/eleicoes/anos").json()
        meta["ultimoAnoEleicao"] = ano
        meta["anosEleicao"] = anos

        for lista in LISTAS:
            params = {"anoEleicao": ano} if lista == "responsaveis-fins-eleitorais" else {}
            # 1) endpoint oficial, JSON, lista inteira
            esperar()
            t0 = time.perf_counter()
            r = c.post(f"{BASE}/{lista}", params=params, json={})
            reg = {
                "lista": lista,
                "formato": "json",
                "url": str(r.url),
                "status": r.status_code,
                "segundos": round(time.perf_counter() - t0, 2),
                "bytes": len(r.content),
                "content_type": r.headers.get("content-type"),
            }
            if r.status_code == 200:
                dados = r.json()
                reg["itens"] = len(dados) if isinstance(dados, list) else None
                (DOWNLOADS / f"tcu_{lista}.json").write_bytes(r.content)
            else:
                reg["corpo"] = r.text[:500]
            meta["chamadas"].append(reg)
            print(reg)

            # 2) exportação CSV usada pelo frontend
            esperar()
            t0 = time.perf_counter()
            r = c.post(
                f"{BASE}/{lista}/exportar-para-csv",
                params={"paginaAtual": 1, "tamanhoPagina": 50000, **params},
                json={},
            )
            reg = {
                "lista": lista,
                "formato": "csv",
                "url": str(r.url),
                "status": r.status_code,
                "segundos": round(time.perf_counter() - t0, 2),
                "bytes": len(r.content),
                "content_type": r.headers.get("content-type"),
            }
            if r.status_code == 200:
                (DOWNLOADS / f"tcu_{lista}.csv").write_bytes(r.content)
            else:
                reg["corpo"] = r.text[:500]
            meta["chamadas"].append(reg)
            print(reg)

    (DOWNLOADS / "tcu_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
