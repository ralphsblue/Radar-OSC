"""Baixa o HTML e os bundles JS do frontend certidoes-apf.apps.tcu.gov.br.

Uso: .venv\\Scripts\\python fase0\\tcu\\baixar_frontend.py
Salva tudo em fase0/tcu/respostas/frontend/.
"""
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import httpx

UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
BASE = "https://certidoes-apf.apps.tcu.gov.br/"
OUT = Path(__file__).parent / "respostas" / "frontend"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=30) as c:
        r = c.get(BASE)
        print(r.status_code, r.url, r.headers.get("content-type"))
        (OUT / "index.html").write_text(r.text, encoding="utf-8")
        refs = re.findall(r'(?:src|href)="([^"]+\.(?:js|json|webmanifest))"', r.text)
        for ref in dict.fromkeys(refs):
            time.sleep(1.5)
            url = urljoin(str(r.url), ref)
            rr = c.get(url)
            name = re.sub(r"[^A-Za-z0-9._-]", "_", ref.split("?")[0].strip("/"))
            (OUT / name).write_text(rr.text, encoding="utf-8")
            print(rr.status_code, url, len(rr.text))


if __name__ == "__main__":
    main()
