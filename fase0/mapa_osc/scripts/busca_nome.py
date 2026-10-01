"""Busca OSCs por nome no autocomplete publico e mostra id_osc, CNPJ e indice de preenchimento.
Uso: python busca_nome.py "texto" [max]
"""
import sys, time, httpx
UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
B = "https://mapaosc.ipea.gov.br/api/api/"
c = httpx.Client(headers={"User-Agent": UA}, timeout=40)
r = c.get(B + "busca/osc-autocomplete", params={"texto_busca": sys.argv[1]}).json()
for it in r[: int(sys.argv[2]) if len(sys.argv) > 2 else 5]:
    time.sleep(1.5)
    ip = c.get(B + f"osc/indice_preenchimento/{it['id_osc']}").json()
    time.sleep(1.5)
    ce = c.get(B + f"osc/certificados/{it['id_osc']}").json()
    certs = [(x.get("dc_certificado", {}) or {}).get("tx_nome_certificado", x.get("cd_certificado")) for x in ce] if isinstance(ce, list) else ce
    print(it["id_osc"], it["cd_identificador_osc"], it["tx_razao_social_osc"][:50], "| indice", ip.get("transparencia_osc"), "| certs", certs)
