import json
from pathlib import Path
from typing import Any

FIXTURES_TCU = Path(__file__).parent.parent / "fixtures" / "bases" / "tcu"
ARQUIVOS = {
    "tcu_inidoneos": "20261002_tcu_inidoneos.json",
    "tcu_contas_irregulares": "20261001_tcu_contas_irregulares.json",
    "tcu_inabilitados": "20261001_tcu_inabilitados.json",
}

type Item = dict[str, Any]


def fixture(fonte: str) -> Path:
    return FIXTURES_TCU / ARQUIVOS[fonte]


def ler_fixture(fonte: str) -> list[Item]:
    itens: list[Item] = json.loads(fixture(fonte).read_text(encoding="utf-8"))
    return itens


def gravar_json(caminho: Path, itens: list[Item]) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(itens, ensure_ascii=False), encoding="utf-8")
    return caminho


def alterar(item: Item, **campos: Any) -> Item:
    return {**item, **campos}
