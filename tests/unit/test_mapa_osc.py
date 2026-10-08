import asyncio
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from tests.apoio.evidencias_em_memoria import EvidenciasEmMemoria
from validador_osc.dominio.coleta import Coleta, Falha, MotivoFalha, NaoEncontrado, Obtido, RefEvidencia
from validador_osc.dominio.resultado import Estado
from validador_osc.dominio.tipos import PerfilMapa
from validador_osc.fontes.http import ClienteHttp, PoliticaRetry
from validador_osc.fontes.mapa_osc import FONTE_BUSCA, FonteMapaOsc
from validador_osc.fontes.normalizacao.comum import ErroFormato
from validador_osc.fontes.normalizacao.mapa_osc import localizar_osc, normalizar_perfil
from validador_osc.regras.verificacoes.mapa import verificar_mapa_osc

FIXTURES = Path(__file__).parent.parent / "fixtures" / "fontes" / "mapa_osc"
OKBR = ("okbr", "19131243000197", 621480)
ABRINQ = ("abrinq", "38894796000146", 594130)
SECOES = ("dados_gerais", "descricao", "areas_atuacao_rep", "indice_preenchimento")


def ler(nome: str) -> bytes:
    return (FIXTURES / f"{nome}.json").read_bytes()


def perfil(prefixo: str, cnpj: str) -> PerfilMapa:
    localizado = localizar_osc(ler(f"{prefixo}_busca_cnpj"), cnpj)
    assert localizado is not None
    id_osc, situacao = localizado
    return normalizar_perfil(id_osc, cnpj, situacao, *(ler(f"{prefixo}_{s}") for s in SECOES))


class TestNormalizacao:
    def test_okbr_so_dados_automaticos(self) -> None:
        resultado = perfil("okbr", OKBR[1])
        assert resultado.id_osc == OKBR[2]
        assert resultado.indice_preenchimento == pytest.approx(18.75)
        assert resultado.campos_autodeclarados == ()
        assert not resultado.preenchido_pela_osc

    def test_abrinq_preenchido_pela_osc(self) -> None:
        resultado = perfil("abrinq", ABRINQ[1])
        assert resultado.campos_autodeclarados == (
            "dados_gerais.site",
            "descricao.missao_osc",
            "descricao.visao_osc",
        )

    def test_busca_sem_igualdade_exata_e_ausente(self) -> None:
        assert localizar_osc(ler("okbr_busca_cnpj"), "19131243000278") is None
        assert localizar_osc(ler("ausente_busca_cnpj"), OKBR[1]) is None

    def test_cnpj_com_zero_a_esquerda_e_comparado_com_14_digitos(self) -> None:
        corpo = b'[{"id_osc": 1, "cd_identificador_osc": "191312430001", "cd_situacao_cadastral": 2}]'
        assert localizar_osc(corpo, "00191312430001") == (1, 2)

    @pytest.mark.parametrize("corpo", [b"{", b'{"a": 1}', b'[{"cd_identificador_osc": "19131243000197"}]'])
    def test_formato_inesperado(self, corpo: bytes) -> None:
        with pytest.raises(ErroFormato):
            localizar_osc(corpo, OKBR[1])


class Rotas:
    def __init__(self, prefixo: str, id_osc: int, status: int = 200) -> None:
        self.prefixo = prefixo
        self.id_osc = id_osc
        self.status = status
        self.chamadas: Counter[str] = Counter()

    def responder(self, request: httpx.Request) -> httpx.Response:
        caminho = request.url.path.removeprefix("/api/api/")
        self.chamadas[caminho] += 1
        if self.status != 200:
            return httpx.Response(self.status)
        if caminho.startswith("busca/cnpj/"):
            return httpx.Response(200, content=ler(f"{self.prefixo}_busca_cnpj"))
        secao = caminho.removeprefix("osc/").removesuffix(f"/{self.id_osc}")
        return httpx.Response(200, content=ler(f"{self.prefixo}_{secao}"))


def consultar(rotas: Rotas, evidencias: EvidenciasEmMemoria, cnpj: str) -> Coleta[PerfilMapa]:
    async def nao_dormir(_: float) -> None:
        return None

    async def rodar() -> Coleta[PerfilMapa]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(rotas.responder)) as cliente:
            http = ClienteHttp(cliente, PoliticaRetry(tentativas=1), dormir=nao_dormir)
            return await FonteMapaOsc(http, evidencias).consultar(cnpj)

    return asyncio.run(rodar())


class TestFonte:
    def test_perfil_obtido_e_cacheado_por_30_dias(self) -> None:
        rotas, evidencias = Rotas("abrinq", ABRINQ[2]), EvidenciasEmMemoria()
        primeira = consultar(rotas, evidencias, ABRINQ[1])
        segunda = consultar(rotas, evidencias, ABRINQ[1])
        assert isinstance(primeira, Obtido)
        assert primeira.dados.preenchido_pela_osc
        assert isinstance(segunda, Obtido)
        assert segunda.evidencia.de_cache
        assert rotas.chamadas["busca/cnpj/38894796000146"] == 1
        assert sum(rotas.chamadas.values()) == 1 + len(SECOES)

    def test_busca_usa_cnpj_sem_zeros_a_esquerda(self) -> None:
        rotas = Rotas("okbr", OKBR[2])
        consultar(rotas, EvidenciasEmMemoria(), "01131243000197")
        assert "busca/cnpj/1131243000197" in rotas.chamadas

    def test_ausente_vira_nao_encontrado(self) -> None:
        rotas = Rotas("ausente", 0)
        assert isinstance(consultar(rotas, EvidenciasEmMemoria(), OKBR[1]), NaoEncontrado)

    def test_falha_vira_falha_gravada(self) -> None:
        evidencias = EvidenciasEmMemoria()
        resultado = consultar(Rotas("okbr", OKBR[2], status=503), evidencias, OKBR[1])
        assert isinstance(resultado, Falha)
        assert resultado.motivo is MotivoFalha.HTTP_5XX
        assert evidencias.de(FONTE_BUSCA)


EVIDENCIA = RefEvidencia(1, FONTE_BUSCA, "c" * 64, datetime(2026, 10, 1, tzinfo=UTC))


class TestVerificacao:
    def test_preenchido(self) -> None:
        resultado = verificar_mapa_osc(Obtido(perfil("abrinq", ABRINQ[1]), EVIDENCIA))
        assert (resultado.estado, resultado.situacao) == (Estado.OK, "PREENCHIDO")
        assert "594130" in str(resultado.achados[0].dados["url"])

    def test_automatico(self) -> None:
        resultado = verificar_mapa_osc(Obtido(perfil("okbr", OKBR[1]), EVIDENCIA))
        assert (resultado.estado, resultado.situacao) == (Estado.OK, "AUTOMATICO")
        assert "19 de 100" in resultado.mensagem

    def test_ausente_e_alerta(self) -> None:
        resultado = verificar_mapa_osc(NaoEncontrado(EVIDENCIA))
        assert (resultado.estado, resultado.situacao) == (Estado.ALERTA, "AUSENTE")

    def test_falha_e_indisponivel(self) -> None:
        resultado = verificar_mapa_osc(Falha(MotivoFalha.TIMEOUT, "lento"))
        assert resultado.estado is Estado.INDISPONIVEL
