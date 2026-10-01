"""Consulta agora as fontes reais para cada caso de referência e salva as respostas.

Fontes por CNPJ numérico com DV válido:
- OpenCNPJ cadastral:  https://api.opencnpj.org/{cnpj}
- OpenCNPJ sanções:    https://api.opencnpj.org/{cnpj}?datasets=ceis,cepim,cnep
- TCU consolidada:     https://certidoes-apf.apps.tcu.gov.br/api/rest/publico/certidoes/{cnpj}?seEmitirPDF=false
- Mapa das OSCs:       https://mapaosc.ipea.gov.br/api/api/busca/cnpj/{cnpj sem zeros à esquerda}
  (+ osc/dados_gerais e osc/descricao quando presente, para dizer quem preencheu o perfil)

Se o CNPJ for de filial (ordem diferente de 0001), consulta também a matriz (D5).
CNPJ alfanumérico real: só o OpenCNPJ cadastral, para documentar (D4 deixa fora do MVP).

Uso: .venv/Scripts/python fase0/casos/coletar.py [CNPJ ...]   (sem argumentos: todos os casos)
Saída: respostas/<cnpj>/{opencnpj,opencnpj_datasets,tcu,mapa_busca,mapa_dados_gerais,mapa_descricao}.json
"""

from __future__ import annotations

import sys

from casos_def import CANDIDATOS_AUSENTE_MAPA, CASOS
from comum import RESPOSTAS, baixar, cliente_http, cnpj_da_matriz, validar

OPENCNPJ = "https://api.opencnpj.org/{}"
OPENCNPJ_DS = "https://api.opencnpj.org/{}?datasets=ceis,cepim,cnep"
TCU = "https://certidoes-apf.apps.tcu.gov.br/api/rest/publico/certidoes/{}?seEmitirPDF=false"
MAPA_BUSCA = "https://mapaosc.ipea.gov.br/api/api/busca/cnpj/{}"
MAPA_SECAO = "https://mapaosc.ipea.gov.br/api/api/osc/{}/{}"


def coletar_numerico(cliente, cnpj: str) -> None:
    pasta = RESPOSTAS / cnpj
    baixar(cliente, OPENCNPJ.format(cnpj), pasta / "opencnpj.json")
    baixar(cliente, OPENCNPJ_DS.format(cnpj), pasta / "opencnpj_datasets.json")
    baixar(cliente, TCU.format(cnpj), pasta / "tcu.json")
    busca = baixar(cliente, MAPA_BUSCA.format(cnpj.lstrip("0")), pasta / "mapa_busca.json")
    itens = busca["corpo"] if isinstance(busca["corpo"], list) else []
    exatos = [i for i in itens if str(i.get("cd_identificador_osc", "")).zfill(14) == cnpj]
    if exatos:
        id_osc = exatos[0]["id_osc"]
        baixar(cliente, MAPA_SECAO.format("dados_gerais", id_osc), pasta / "mapa_dados_gerais.json")
        baixar(cliente, MAPA_SECAO.format("descricao", id_osc), pasta / "mapa_descricao.json")


def main(alvos: list[str]) -> None:
    feitos: set[str] = set()
    with cliente_http() as cliente:
        for cnpj in alvos:
            dv = validar(cnpj)
            if not dv.valido:
                print(f"-- {cnpj}: DV/formato inválido, nada a consultar")
                continue
            if not cnpj.isdigit():
                print(f"-- {cnpj}: alfanumérico, só OpenCNPJ cadastral (documentação)")
                baixar(cliente, OPENCNPJ.format(cnpj), RESPOSTAS / cnpj / "opencnpj.json")
                continue
            lista = [cnpj]
            if cnpj[8:12] != "0001":
                lista.append(cnpj_da_matriz(cnpj))
            for c in lista:
                if c not in feitos:
                    coletar_numerico(cliente, c)
                    feitos.add(c)


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args or [c["cnpj"] for c in CASOS] + CANDIDATOS_AUSENTE_MAPA)
