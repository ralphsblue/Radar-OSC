"""Baixa o XML mensal (ZIP) do DOU publicado pela Imprensa Nacional.

Uso:
    python baixar_dou.py 2026 Agosto            # baixa S01 do mes
    python baixar_dou.py 2026 Agosto S01 S02    # outras secoes

Fonte: https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados
A pagina lista os ZIPs de cada mes em ?ano=AAAA&mes=NomeDoMes (sem login).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
BASE = "https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados"
DOWNLOADS = Path(__file__).parent / "downloads"
PAUSA_S = 2.0


def listar_zips(cliente: httpx.Client, ano: int, mes: str) -> dict[str, str]:
    r = cliente.get(BASE, params={"ano": str(ano), "mes": mes})
    r.raise_for_status()
    links = re.findall(r'href="(https://www\.in\.gov\.br/documents/[^"]+?/([A-Z0-9]+)\.zip/[^"]+)"', r.text)
    return {nome: url.replace("&amp;", "&") for url, nome in links}


def baixar(cliente: httpx.Client, url: str, destino: Path) -> dict:
    sha = hashlib.sha256()
    with cliente.stream("GET", url) as r:
        r.raise_for_status()
        with destino.open("wb") as f:
            for bloco in r.iter_bytes(1 << 20):
                f.write(bloco)
                sha.update(bloco)
    return {
        "url": url,
        "arquivo": destino.name,
        "bytes": destino.stat().st_size,
        "sha256": sha.hexdigest(),
        "baixado_em": datetime.now(UTC).isoformat(),
    }


def main() -> None:
    ano = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    mes = sys.argv[2] if len(sys.argv) > 2 else "Agosto"
    secoes = sys.argv[3:] or ["S01"]
    DOWNLOADS.mkdir(exist_ok=True)
    with httpx.Client(headers={"User-Agent": UA}, timeout=120, follow_redirects=True) as cliente:
        zips = listar_zips(cliente, ano, mes)
        print(f"ZIPs listados para {mes}/{ano}: {sorted(zips)}")
        for nome, url in sorted(zips.items()):
            if not any(nome.startswith(s) for s in secoes):
                continue
            destino = DOWNLOADS / f"{nome}.zip"
            if destino.exists():
                print(f"ja existe: {destino.name}")
                continue
            time.sleep(PAUSA_S)
            meta = baixar(cliente, url, destino)
            (DOWNLOADS / f"{nome}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
            print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
