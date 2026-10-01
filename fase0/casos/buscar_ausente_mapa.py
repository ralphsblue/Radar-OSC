"""Procura uma associação Ativa ausente do Mapa das OSCs.

A base do Mapa (coleta de agosto/2026) vai até CNPJs abertos em junho/2026
(raiz ~67,5 milhões). Associações abertas depois disso ainda não estão no Mapa.
Sorteia raízes entre 68.000.000 e 69.600.000 com ordem 0001 (DV calculado),
consulta o OpenCNPJ (espelho de 15/09/2026) até achar uma Associação Privada
Ativa e confirma a ausência na API do Mapa.

Semente fixa para reprodutibilidade. Limite: 150 consultas ao OpenCNPJ.

Uso: .venv/Scripts/python fase0/casos/buscar_ausente_mapa.py [semente]  (rodado com 20261001 e 7)
Saída: respostas/busca_ausente_mapa/
"""

from __future__ import annotations

import json
import random
import sys

from comum import RESPOSTAS, baixar, cliente_http

from validador_osc.cnpj import calcular_dvs

PASTA = RESPOSTAS / "busca_ausente_mapa"
SEMENTE = int(sys.argv[1]) if len(sys.argv) > 1 else 20261001
LIMITE = 150


def main() -> None:
    rng = random.Random(SEMENTE)
    resumo = {"semente": SEMENTE, "consultas": 0, "naturezas": {}, "achado": None}
    with cliente_http() as cliente:
        for _ in range(LIMITE):
            base = f"{rng.randint(68_000_000, 69_600_000):08d}0001"
            cnpj = base + calcular_dvs(base)
            reg = baixar(cliente, f"https://api.opencnpj.org/{cnpj}", PASTA / f"opencnpj_{cnpj}.json")
            resumo["consultas"] += 1
            c = reg["corpo"] if reg["meta"]["status"] == 200 else None
            if not c:
                continue
            nat = c.get("natureza_juridica", "")
            resumo["naturezas"][nat] = resumo["naturezas"].get(nat, 0) + 1
            if nat != "Associação Privada" or c.get("situacao_cadastral") != "Ativa":
                (PASTA / f"opencnpj_{cnpj}.json").unlink()  # não guarda dados de empresas/MEI sem uso
                continue
            busca = baixar(
                cliente,
                f"https://mapaosc.ipea.gov.br/api/api/busca/cnpj/{cnpj.lstrip('0')}",
                PASTA / f"mapa_{cnpj}.json",
            )
            itens = busca["corpo"] if isinstance(busca["corpo"], list) else []
            if not any(str(i.get("cd_identificador_osc", "")).zfill(14) == cnpj for i in itens):
                resumo["achado"] = {
                    "cnpj": cnpj,
                    "razao_social": c["razao_social"],
                    "inicio": c.get("data_inicio_atividade"),
                    "cnae": c.get("cnae_principal"),
                }
                print(f"  ACHADO: {cnpj} {c['razao_social']} {c.get('data_inicio_atividade')}")
                break
    (PASTA / f"_resumo_{SEMENTE}.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(resumo, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
