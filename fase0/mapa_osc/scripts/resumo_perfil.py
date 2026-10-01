"""Aplica a regra de interpretacao (rascunho) sobre as respostas salvas por probe_osc.py.
Uso: python resumo_perfil.py prefixo [prefixo ...]
Regra: um dado e "preenchido pela OSC" quando o valor nao e nulo/vazio E a fonte (ft_*) e "Representante de OSC"
ou o registro tem bo_oficial = false. ft_* = "Representante de OSC" com valor nulo e so o default do banco.
"""
import sys, json, pathlib, datetime
R = pathlib.Path(__file__).resolve().parent.parent / "respostas"
REP = "Representante de OSC"
CEBAS = {2: "CEBAS - Educacao", 3: "CEBAS - Saude", 6: "CEBAS - Assistencia Social"}

def load(p, n):
    f = R / f"{p}_{n}.json"
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None

def autodeclarados_obj(d):
    """Campos tx_/nr_/dt_ com ft_ correspondente == Representante e valor preenchido."""
    out = []
    if not isinstance(d, dict):
        return out
    for k, v in d.items():
        if not k.startswith("ft_") or v != REP:
            continue
        base = k[3:]
        for pref in ("tx_", "nr_", "dt_", "cd_", "im_", "bo_", ""):
            val = d.get(pref + base)
            if val not in (None, "", [], False):
                out.append(pref + base); break
    return out

for p in sys.argv[1:]:
    log = load(p, "_log") or json.loads((R / f"{p}__log.json").read_text(encoding="utf-8"))
    if not log.get("id_osc"):
        print(json.dumps({"prefixo": p, "presente_no_mapa": False}, ensure_ascii=False)); continue
    dg, cab, desc = load(p, "dados_gerais"), load(p, "cabecalho"), load(p, "descricao")
    idx, certs, gov = load(p, "indice_preenchimento"), load(p, "certificados"), load(p, "rel_trabalho_e_governanca")
    ps, proj, rec, rep_area = load(p, "participacao_social"), load(p, "projetos"), load(p, "anos_recursos"), load(p, "areas_atuacao_rep")
    certs = certs if isinstance(certs, list) else []
    hoje = datetime.date.today().isoformat()
    cert_out = [{"tipo": c["dc_certificado"]["tx_nome_certificado"], "cd": c["cd_certificado"], "fonte": c["ft_certificado"],
                 "oficial": c["bo_oficial"], "inicio": c["dt_inicio_certificado"], "fim": c["dt_fim_certificado"],
                 "vigente_pelo_mapa": (c["dt_fim_certificado"] or "9999") >= hoje} for c in certs]
    descr_preenchida = [k for k, v in (desc or {}).items() if k.startswith("tx_") and v]
    auto = autodeclarados_obj(dg) + autodeclarados_obj(cab) + descr_preenchida
    secoes_osc = {
        "descricao": bool(descr_preenchida),
        "areas_atuacao_declaradas": bool(rep_area),
        "governanca_dirigentes": bool((gov or {}).get("governanca")),
        "conselho_fiscal": bool((gov or {}).get("conselho_fiscal")),
        "participacao_social": any((ps or {}).values()),
        "certificado_autodeclarado": any(not c["oficial"] for c in cert_out),
    }
    print(json.dumps({
        "prefixo": p, "presente_no_mapa": True, "id_osc": log["id_osc"],
        "url_perfil": f"https://mapaosc.ipea.gov.br/detalhar/{log['id_osc']}",
        "indice_preenchimento": (idx or {}).get("transparencia_osc"),
        "campos_autodeclarados": auto,
        "secoes_preenchidas_pela_osc": secoes_osc,
        # anos_recursos e projetos misturam fontes oficiais (SIGABR, SICONV) e autodeclaradas;
        # por isso entram so como contexto e nao contam para "perfil preenchido pela OSC".
        "anos_com_recursos_qualquer_fonte": rec if isinstance(rec, list) else [],
        "n_projetos_total": len(proj) if isinstance(proj, list) else 0,
        "certificados": cert_out,
        "cebas_no_mapa": [c for c in cert_out if c["cd"] in CEBAS],
        "perfil": "preenchido_pela_osc" if (auto or any(secoes_osc.values())) else "so_dados_automaticos",
    }, ensure_ascii=False, indent=1))
