"""Consulta, por CNPJ, os endpoints publicos da API do Mapa das OSCs (Ipea) e salva as respostas brutas.
Uso: python probe_osc.py CNPJ [prefixo_saida]
Base: https://mapaosc.ipea.gov.br/api/api/ (rotas em Plataformas-Cidadania/mapa-osc-api, routes/web.php)
"""
import sys, time, json, hashlib, pathlib, datetime, httpx

UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
BASE = "https://mapaosc.ipea.gov.br/api/api/"
OUT = pathlib.Path(__file__).resolve().parent.parent / "respostas"
cnpj = "".join(c for c in sys.argv[1] if c.isalnum())
prefixo = sys.argv[2] if len(sys.argv) > 2 else cnpj

cli = httpx.Client(headers={"User-Agent": UA, "Accept": "application/json"}, timeout=40, follow_redirects=True)
log = []

def get(path, nome, params=None):
    time.sleep(1.5)
    t0 = time.time()
    try:
        r = cli.get(BASE + path, params=params)
    except Exception as e:
        log.append({"path": path, "erro": repr(e)})
        print(f"ERRO {path}: {e!r}")
        return None
    dt = time.time() - t0
    (OUT / f"{prefixo}_{nome}.json").write_bytes(r.content)
    log.append({"path": path, "params": params, "status": r.status_code, "tempo_s": round(dt, 2),
                "bytes": len(r.content), "sha256": hashlib.sha256(r.content).hexdigest(),
                "data": datetime.datetime.now().isoformat(timespec="seconds")})
    print(f"{r.status_code} {dt:5.2f}s {len(r.content):7d}B {path}")
    try:
        return r.json()
    except Exception:
        return None

# 1) CNPJ -> id_osc (rota usada pelo front na busca da home)
busca = get("busca/osc-autocomplete", "busca", {"texto_busca": cnpj})
alt = get(f"busca/cnpj/{cnpj}", "busca_cnpj")
id_osc = None
for lista in (busca, alt):
    if isinstance(lista, list):
        for item in lista:
            if str(item.get("cd_identificador_osc", "")).zfill(14) == cnpj.zfill(14):
                id_osc = item["id_osc"]
if id_osc is None:
    print("CNPJ nao encontrado no Mapa das OSCs")
else:
    print("id_osc =", id_osc)
    for path, nome in [
        (f"osc/{id_osc}", "osc"),
        (f"osc/cabecalho/{id_osc}", "cabecalho"),
        (f"osc/dados_gerais/{id_osc}", "dados_gerais"),
        (f"osc/indice_preenchimento/{id_osc}", "indice_preenchimento"),
        (f"osc/areas_atuacao/{id_osc}", "areas_atuacao"),
        (f"osc/areas_atuacao_rep/{id_osc}", "areas_atuacao_rep"),
        (f"osc/descricao/{id_osc}", "descricao"),
        (f"osc/certificados/{id_osc}", "certificados"),
        (f"osc/rel_trabalho_e_governanca/{id_osc}", "rel_trabalho_e_governanca"),
        (f"osc/participacao_social/{id_osc}", "participacao_social"),
        (f"osc/projetos/{id_osc}", "projetos"),
        (f"osc/anos_recursos/{id_osc}", "anos_recursos"),
        (f"osc/quadro-societario-por-osc/{id_osc}", "quadro_societario"),
        (f"osc/popup/{id_osc}", "popup"),
    ]:
        get(path, nome)

(OUT / f"{prefixo}__log.json").write_text(json.dumps({"cnpj": cnpj, "id_osc": id_osc, "chamadas": log}, indent=1, ensure_ascii=False), encoding="utf-8")
