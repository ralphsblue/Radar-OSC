import csv
import zipfile
from pathlib import Path

from validador_osc.pessoa_fisica import calcular_dvs

FIXTURES_CGU = Path(__file__).parent / "fixtures" / "bases" / "cgu"
ARQUIVOS = {"CEPIM": "20260928_CEPIM.csv", "CEIS": "20260930_CEIS.csv", "CNEP": "20260930_CNEP.csv"}

type Tabela = tuple[list[str], list[list[str]]]


def fixture(cadastro: str) -> Path:
    return FIXTURES_CGU / ARQUIVOS[cadastro]


def ler_fixture(cadastro: str) -> Tabela:
    with fixture(cadastro).open(encoding="iso-8859-1", newline="") as arquivo:
        cabecalho, *linhas = csv.reader(arquivo, delimiter=";")
    return cabecalho, linhas


def gravar_csv(caminho: Path, tabela: Tabela) -> Path:
    cabecalho, linhas = tabela
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="iso-8859-1", newline="") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)
    return caminho


def compactar(csv_origem: Path, destino: Path) -> Path:
    with zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_DEFLATED) as arquivo:
        arquivo.write(csv_origem, csv_origem.name)
    return destino


def alterar(cabecalho: list[str], linha: list[str], campos: dict[str, str]) -> list[str]:
    valores = dict(zip(cabecalho, linha, strict=True))
    valores.update(campos)
    return [valores[coluna] for coluna in cabecalho]


def cpf_sintetico(semente: int) -> str:
    base = f"{100_000_000 + semente * 7_919:09d}"
    return base + calcular_dvs(base)


def formatar_cpf(cpf: str) -> str:
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
