from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import httpx

UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
PAGINA_OFICIAL = (
    "https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/consultas/dados-publicos-cnpj"
)
COMPARTILHAMENTO = "https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9"
WEBDAV = "https://arquivos.receitafederal.gov.br/public.php/webdav"
TOKEN = "YggdBLfdninEJX9"
REFERENCIA = "https://concla.ibge.gov.br/estrutura/natjur-estrutura/natureza-juridica-2021"

PASTA = Path(__file__).parent
RAIZ = PASTA.parents[1]
COPIA_FONTE = PASTA / "naturezas_receita.csv"
SAIDA = RAIZ / "validador_osc" / "dados" / "natureza_juridica.json"

SENTINELAS = {
    0: "Valor da Receita para natureza não informada; não é código da tabela.",
    8885: "Valor da Receita para natureza não informada; não é código da tabela.",
}

ELEGIVEL = "ELEGIVEL"
RELIGIOSA = "ELEGIVEL_COM_ALERTA_RELIGIOSO"
REVISAO = "REVISAO_MANUAL"
NAO = "NAO_ELEGIVEL"

REGRAS: dict[int, tuple[str, str]] = {
    3999: (
        ELEGIVEL,
        "Entidade privada sem fins lucrativos: Lei 13.019/2014, art. 2º, I, a. "
        "O não lucro em si não é verificável pela Receita e fica como premissa.",
    ),
    3069: (
        ELEGIVEL,
        "Fundação de direito privado sem fins lucrativos: Lei 13.019/2014, art. 2º, I, a.",
    ),
    3220: (
        RELIGIOSA,
        "Organização religiosa: Lei 13.019/2014, art. 2º, I, c, só quando atua em atividades de interesse "
        "público e cunho social distintas das exclusivamente religiosas; sujeita à verificação `religiosa`.",
    ),
    2143: (
        REVISAO,
        "Cooperativa: só as do art. 2º, I, b da Lei 13.019/2014 (Lei 9.867/1999, pessoas em situação de risco, "
        "combate à pobreza, trabalhadores rurais, interesse público). [ORIENTADOR Q14]",
    ),
    2330: (
        REVISAO,
        "Cooperativa de consumo: é cooperativa e por isso segue a regra de 214-3 (art. 2º, I, b da "
        "Lei 13.019/2014), código criado depois da tabela do spec. [ORIENTADOR Q14]",
    ),
    3301: (
        REVISAO,
        "Organização Social: contratos de gestão com OS estão fora do MROSC (Lei 13.019/2014, art. 3º, III), "
        "mas a entidade pode firmar outras parcerias como associação ou fundação. [ORIENTADOR Q14]",
    ),
    3204: (
        REVISAO,
        "Estabelecimento no Brasil de fundação ou associação estrangeira: pode ser entidade sem fins lucrativos "
        "do art. 2º, I, a, mas depende de autorização de funcionamento e do estatuto. [ORIENTADOR Q14]",
    ),
    3077: (
        NAO,
        "Serviço Social Autônomo (Sistema S): parcerias com essas entidades estão fora do MROSC "
        "(Lei 13.019/2014, art. 3º, X). [ORIENTADOR Q14]",
    ),
    3034: (NAO, "Serviço notarial e registral é delegação do poder público, não OSC (art. 2º, I)."),
    3085: (NAO, "Condomínio edilício não é entidade associativa de interesse público (art. 2º, I)."),
    3107: (NAO, "Comissão de conciliação prévia é instância trabalhista, não OSC (art. 2º, I)."),
    3115: (NAO, "Entidade de mediação e arbitragem presta serviço de solução de conflitos, não é OSC (art. 2º, I)."),
    3131: (
        NAO,
        "Entidade sindical tem regime constitucional próprio (CF, art. 8º) e fica fora do conceito de OSC "
        "adotado pelo projeto e pelo Mapa das OSCs.",
    ),
    3212: (
        NAO,
        "Fundação ou associação domiciliada no exterior, sem estabelecimento no Brasil; "
        "o estabelecimento no Brasil é o código 320-4.",
    ),
    3239: (
        NAO,
        "Comunidade indígena não está entre os tipos do art. 2º, I; quando atua como OSC, "
        "costuma fazê-lo por associação privada (399-9).",
    ),
    3247: (NAO, "Fundo privado é patrimônio sem personalidade associativa, não OSC (art. 2º, I)."),
    3328: (NAO, "Plano de previdência complementar fechada não é OSC (art. 2º, I)."),
}

PARTIDOS = {3255, 3263, 3271, 3280, 3298}
JUSTIFICATIVA_PARTIDO = (
    "Partido político e entidades eleitorais têm regime próprio (Lei 9.096/1995) e não são OSC (art. 2º, I)."
)
JUSTIFICATIVA_POR_GRUPO = {
    1: "Administração pública: órgãos e entidades públicas não são OSC (Lei 13.019/2014, art. 2º, I).",
    2: "Entidade empresarial: distribui resultados entre sócios e não é OSC (Lei 13.019/2014, art. 2º, I).",
    4: "Pessoa física ou equiparada: não é OSC (Lei 13.019/2014, art. 2º, I).",
    5: "Organização internacional ou extraterritorial: fora do art. 2º, I da Lei 13.019/2014.",
}

SINONIMOS: dict[int, list[str]] = {
    3301: ["Organização Social"],
}

_ESPACOS = re.compile(r"\s+")


def digito_verificador(radical: int) -> int:
    pesos = (4, 3, 2)
    soma = sum(int(d) * p for d, p in zip(f"{radical:03d}", pesos, strict=True))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def listar_meses(cliente: httpx.Client) -> list[str]:
    resposta = cliente.request("PROPFIND", f"{WEBDAV}/", headers={"Depth": "1"})
    resposta.raise_for_status()
    return sorted(set(re.findall(r"/public\.php/webdav/(\d{4}-\d{2})/", resposta.text)))


def baixar(mes: str | None) -> tuple[bytes, str, str]:
    with httpx.Client(
        timeout=60, follow_redirects=True, headers={"User-Agent": UA}, auth=(TOKEN, "")
    ) as cliente:
        escolhido = mes or listar_meses(cliente)[-1]
        url = f"{WEBDAV}/{escolhido}/Naturezas.zip"
        resposta = cliente.get(url)
        resposta.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resposta.content)) as pacote:
        nomes = pacote.namelist()
        if len(nomes) != 1:
            raise SystemExit(f"Esperado um arquivo em Naturezas.zip, encontrados {nomes}")
        return pacote.read(nomes[0]), url, nomes[0]


def ler_csv(bruto: bytes) -> list[tuple[int, str]]:
    leitor = csv.reader(io.StringIO(bruto.decode("latin-1")), delimiter=";", quotechar='"')
    linhas = []
    for registro in leitor:
        if not registro:
            continue
        codigo, descricao = registro
        linhas.append((int(codigo), _ESPACOS.sub(" ", descricao).strip()))
    return linhas


def regra_de(codigo: int) -> tuple[str, str]:
    if codigo in REGRAS:
        return REGRAS[codigo]
    if codigo in PARTIDOS or codigo == 4090:
        return NAO, JUSTIFICATIVA_PARTIDO
    grupo = codigo // 1000
    if grupo in JUSTIFICATIVA_POR_GRUPO:
        return NAO, JUSTIFICATIVA_POR_GRUPO[grupo]
    raise SystemExit(f"Código {codigo} sem regra definida; revise REGRAS")


def montar(linhas: list[tuple[int, str]]) -> list[dict[str, object]]:
    itens = []
    vistos: set[int] = set()
    for codigo, descricao in linhas:
        if codigo in SENTINELAS:
            continue
        if codigo in vistos:
            raise SystemExit(f"Código duplicado na fonte: {codigo}")
        vistos.add(codigo)
        radical, dv = divmod(codigo, 10)
        if digito_verificador(radical) != dv:
            raise SystemExit(f"DV inválido na fonte: {codigo}")
        regra, justificativa = regra_de(codigo)
        itens.append(
            {
                "codigo": codigo,
                "codigo_formatado": f"{radical:03d}-{dv}",
                "descricao": descricao,
                "sinonimos": SINONIMOS.get(codigo, []),
                "regra": regra,
                "justificativa": justificativa,
            }
        )
    faltando = (set(REGRAS) | set(SINONIMOS)) - vistos
    if faltando:
        raise SystemExit(f"Códigos com regra ou sinônimo ausentes da fonte: {sorted(faltando)}")
    return sorted(itens, key=lambda item: int(str(item["codigo"])))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mes", help="pasta mensal dos dados abertos (AAAA-MM); padrão: a mais recente")
    parser.add_argument("--offline", action="store_true", help=f"usa a cópia salva em {COPIA_FONTE.name}")
    args = parser.parse_args()
    if args.offline:
        metadados_anteriores = json.loads(SAIDA.read_text(encoding="utf-8"))["fonte"]
        bruto = COPIA_FONTE.read_bytes()
        url = str(metadados_anteriores["url_arquivo"])
        arquivo = str(metadados_anteriores["arquivo"])
        baixado_em = str(metadados_anteriores["baixado_em"])
    else:
        bruto, url, arquivo = baixar(args.mes)
        COPIA_FONTE.write_bytes(bruto)
        baixado_em = datetime.now(UTC).isoformat(timespec="seconds")
    linhas = ler_csv(bruto)
    naturezas = montar(linhas)
    contagem: dict[str, int] = {}
    for item in naturezas:
        contagem[str(item["regra"])] = contagem.get(str(item["regra"]), 0) + 1
    documento = {
        "versao": "0.1-proposta",
        "tabela": "Tabela de Natureza Jurídica 2021 (CONCLA/IBGE), na versão publicada pela Receita Federal",
        "fonte": {
            "orgao": "Receita Federal do Brasil - Dados Abertos do CNPJ, arquivo Naturezas",
            "pagina": PAGINA_OFICIAL,
            "compartilhamento": COMPARTILHAMENTO,
            "url_arquivo": url,
            "arquivo": arquivo,
            "sha256": hashlib.sha256(bruto).hexdigest(),
            "baixado_em": baixado_em,
            "referencia_concla": REFERENCIA,
            "gerado_por": "fase0/natureza/gerar_natureza.py",
        },
        "base_legal": "Lei 13.019/2014, art. 2º, I e art. 3º; tabela 6.3 do spec [ORIENTADOR Q14]",
        "como_aplicar": (
            "Código de 4 dígitos (BrasilAPI e Minha Receita) busca pelo campo codigo. "
            "Descrição em texto (OpenCNPJ) busca pela descrição oficial e pelos sinônimos, comparados sem acento, "
            "em minúsculas, com pontuação e espaços colapsados. Natureza sem correspondência = ALERTA (D17)."
        ),
        "excluidos_da_fonte": {f"{c:04d}": motivo for c, motivo in SENTINELAS.items()},
        "contagem": {"total": len(naturezas), **dict(sorted(contagem.items()))},
        "naturezas": naturezas,
    }
    SAIDA.write_text(json.dumps(documento, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Salvo em {SAIDA}: {len(naturezas)} naturezas {contagem}")


if __name__ == "__main__":
    main()
