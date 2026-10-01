import json
from pathlib import Path

PASTA = Path(__file__).parent
ORIGEM = PASTA / "ibge_cnae_subclasses.json"
DESTINO = PASTA.parent.parent / "validador_osc" / "dados" / "cnae_subclasses.json"
NIVEIS = ("divisoes", "grupos", "classes", "subclasses")


def _por_codigo(itens: list[dict[str, object]]) -> dict[str, str]:
    codigos = {str(item["id"]): str(item["descricao"]).strip() for item in itens}
    if len(codigos) != len(itens):
        raise ValueError("Código repetido na estrutura do IBGE")
    return dict(sorted(codigos.items()))


def gerar() -> dict[str, object]:
    ibge = json.loads(ORIGEM.read_text(encoding="utf-8"))
    metadados = ibge["metadados"]
    enxuto: dict[str, object] = {
        "fonte": metadados["fonte"],
        "versao_cnae": metadados["versao_cnae"],
        "baixado_em": metadados["baixado_em"],
    }
    for nivel in NIVEIS:
        enxuto[nivel] = _por_codigo(ibge[nivel])
    return enxuto


def main() -> None:
    texto = json.dumps(gerar(), ensure_ascii=False, indent=1) + "\n"
    DESTINO.write_text(texto, encoding="utf-8", newline="\n")
    print(f"Gerado {DESTINO} ({DESTINO.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
