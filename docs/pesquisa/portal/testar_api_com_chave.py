r"""
Roteiro 19.4 (T1 a T8) da API do Portal da Transparência, com chave.

A chave é lida do .env da raiz do projeto (CHAVE-API-DADOS ou PORTAL_KEY) e usada
apenas no header da requisição. Ela nunca é impressa nem salva: as respostas
gravadas guardam só URL, parâmetros, status, tempo, headers de resposta e corpo.

Uso: .\.venv\Scripts\python fase0\portal\testar_api_com_chave.py
"""

import json
import sys
import time
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = Path(__file__).resolve().parent / "respostas_api"
BASE = "https://api.portaldatransparencia.gov.br/api-de-dados"
UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
PAUSA_S = 1.0


def carregar_chave() -> str:
    env = RAIZ / ".env"
    if not env.exists():
        sys.exit(".env não encontrado na raiz do projeto")
    for linha in env.read_text(encoding="utf-8-sig").splitlines():
        nome, sep, valor = linha.partition("=")
        if sep and nome.strip().upper() in {"CHAVE-API-DADOS", "PORTAL_KEY"}:
            valor = valor.strip().strip('"').strip("'")
            if valor:
                return valor
    sys.exit("Chave não encontrada no .env (esperado CHAVE-API-DADOS=... ou PORTAL_KEY=...)")


CASOS: list[tuple[str, str, dict[str, str | int]]] = [
    # T1 - nada consta (OKBR)
    ("T1_cepim_okbr", "cepim", {"cnpjSancionado": "19131243000197"}),
    ("T1_ceis_okbr", "ceis", {"codigoSancionado": "19131243000197"}),
    ("T1_cnep_okbr", "cnep", {"codigoSancionado": "19131243000197"}),
    # T2 - positivo CEPIM
    ("T2_cepim_bomjesus", "cepim", {"cnpjSancionado": "14112015000156"}),
    ("T2_cepim_pacaembu", "cepim", {"cnpjSancionado": "53524534000183"}),
    # T3 - positivo CEIS/CNEP, vigente e expirado
    ("T3_ceis_vigente_taipas", "ceis", {"codigoSancionado": "00688001000170"}),
    ("T3_ceis_expirado_plural", "ceis", {"codigoSancionado": "03126200000183"}),
    ("T3_ceis_vence_2026", "ceis", {"codigoSancionado": "02393242000118"}),
    ("T3_cnep_ilumina", "cnep", {"codigoSancionado": "08928169000118"}),
    ("T3_cnep_pacaembu", "cnep", {"codigoSancionado": "53524534000183"}),
    # T4 - exato ou por raiz (sanção só na filial 0005-70)
    ("T4_ceis_filial_exata", "ceis", {"codigoSancionado": "44551605000570"}),
    ("T4_ceis_matriz_limpa", "ceis", {"codigoSancionado": "44551605000146"}),
    ("T4_ceis_raiz", "ceis", {"codigoSancionado": "44551605"}),
    ("T4_cepim_raiz_pacaembu", "cepim", {"cnpjSancionado": "53524534"}),
    # T5 - CNPJ formatado
    ("T5_ceis_formatado", "ceis", {"codigoSancionado": "44.551.605/0005-70"}),
    ("T5_cepim_formatado", "cepim", {"cnpjSancionado": "14.112.015/0001-56"}),
    # T7 - paginação (IMDC tem 10 convênios no CEPIM)
    ("T7_cepim_imdc_p1", "cepim", {"cnpjSancionado": "21145289000107"}),
    ("T7_cepim_imdc_p2", "cepim", {"cnpjSancionado": "21145289000107", "pagina": 2}),
    ("T7_ceis_sem_filtro_p1", "ceis", {}),
    # T8 - filtro por nome
    ("T8_ceis_nome_completo", "ceis", {"nomeSancionado": "ASSOCIACAO PLURAL"}),
    ("T8_ceis_nome_parcial", "ceis", {"nomeSancionado": "PLURAL"}),
    ("T8_cepim_nome_parcial", "cepim", {"nomeSancionado": "SANTA CASA"}),
]


def resumo(corpo: object) -> str:
    if isinstance(corpo, list):
        return f"lista com {len(corpo)} registro(s)"
    if isinstance(corpo, dict):
        return "objeto: " + ", ".join(list(corpo)[:5])
    return str(corpo)[:80]


def main() -> None:
    chave = carregar_chave()
    SAIDA.mkdir(exist_ok=True)
    tempos: list[int] = []
    with httpx.Client(timeout=30, headers={"User-Agent": UA}) as cliente:
        for nome, rota, params in CASOS:
            params = {"pagina": 1, **params}
            t0 = time.perf_counter()
            try:
                r = cliente.get(f"{BASE}/{rota}", params=params, headers={"chave-api-dados": chave})
                ms = int((time.perf_counter() - t0) * 1000)
                tempos.append(ms)
                try:
                    corpo = r.json()
                except ValueError:
                    corpo = {"_texto_nao_json": r.text[:2000]}
                registro = {
                    "caso": nome,
                    "url": f"{BASE}/{rota}",
                    "params": params,
                    "http": r.status_code,
                    "ms": ms,
                    "headers_resposta": {
                        k: v
                        for k, v in r.headers.items()
                        if k.lower().startswith(
                            ("x-rate", "ratelimit", "retry", "content-type", "cache-control")
                        )
                    },
                    "corpo": corpo,
                }
                print(f"{nome:<28} HTTP {r.status_code}  {ms:>5} ms  {resumo(corpo)}")
            except httpx.HTTPError as e:
                registro = {"caso": nome, "url": f"{BASE}/{rota}", "params": params, "erro": type(e).__name__}
                print(f"{nome:<28} ERRO {type(e).__name__}")
            (SAIDA / f"{nome}.json").write_text(
                json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            time.sleep(PAUSA_S)
    if tempos:
        tempos.sort()
        print(f"\nlatência: mediana {tempos[len(tempos) // 2]} ms, máx {tempos[-1]} ms, n={len(tempos)}")


if __name__ == "__main__":
    main()
