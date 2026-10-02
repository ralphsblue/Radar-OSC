from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from validador_osc.dominio.bases import CargaAtiva, ConsultaLocal
from validador_osc.dominio.coleta import Falha, MotivoFalha, Obtido, RefEvidencia
from validador_osc.dominio.resultado import Contexto, Esfera, Estado
from validador_osc.dominio.sancoes import (
    CadastroSancao,
    CertidaoTcu,
    ListaTcu,
    RegistroListaTcu,
    RespostaTcu,
    Sancao,
    SituacaoCertidaoTcu,
    TipoCertidaoTcu,
    TipoPessoa,
)
from validador_osc.regras.parametros import (
    CepimEsfera,
    CnepMulta,
    Cnia,
    Raiz,
    carregar_limites,
    carregar_regras_orientador,
)
from validador_osc.regras.verificacoes.sancoes import (
    ObservacoesSancoes,
    verificar_ceis,
    verificar_cepim,
    verificar_cnep,
    verificar_cnj_cnia,
    verificar_tcu_contas_irregulares,
    verificar_tcu_inidoneos,
)

REF = date(2026, 10, 1)
CONTEXTO = Contexto(REF)
REGRAS = carregar_regras_orientador()
LIMITES = carregar_limites()
CNPJ = "19131243000197"
MATRIZ = "19131243000278"
OUTRO = "19131243000359"
FONTES_CARGA = {
    CadastroSancao.CEPIM: "cgu_cepim",
    CadastroSancao.CEIS: "cgu_ceis",
    CadastroSancao.CNEP: "cgu_cnep",
    ListaTcu.INIDONEOS: "tcu_inidoneos",
    ListaTcu.CONTAS_IRREGULARES: "tcu_contas_irregulares",
}


def carga(fonte: str, data_base: date = REF) -> CargaAtiva:
    return CargaAtiva(1, fonte, data_base, datetime(2026, 10, 1, 6, tzinfo=UTC), "a" * 64)


def sancao(cadastro: CadastroSancao = CadastroSancao.CEIS, **alteracoes: Any) -> Sancao:
    base = Sancao(
        cadastro=cadastro,
        tipo_pessoa=TipoPessoa.JURIDICA,
        documento=CNPJ,
        raiz=CNPJ[:8],
        nome="ASSOCIACAO TESTE",
        categoria="Impedimento/proibição de contratar com prazo determinado",
        data_inicio=date(2025, 1, 1),
        data_fim=date(2027, 1, 1),
        orgao="Prefeitura",
        esfera="MUNICIPAL",
        uf="SP",
        abrangencia="Todas as esferas em todos os poderes",
        fundamentacao=None,
        processo="12345678901234567890",
        valor_multa=None,
        codigo_sancao="1",
        origem_informacoes=None,
    )
    return replace(base, **alteracoes)


def locais(*registros: Sancao, data_base: date = REF) -> dict[CadastroSancao, ConsultaLocal[Sancao] | None]:
    saida: dict[CadastroSancao, ConsultaLocal[Sancao] | None] = {}
    for cadastro in CadastroSancao:
        doc = tuple(r for r in registros if r.cadastro is cadastro)
        saida[cadastro] = ConsultaLocal(carga(FONTES_CARGA[cadastro], data_base), doc)
    return saida


def certidao(
    tipo: TipoCertidaoTcu,
    situacao: SituacaoCertidaoTcu = SituacaoCertidaoTcu.NADA_CONSTA,
    observacao: str | None = None,
    datas: tuple[date, ...] = (),
    processos: tuple[str, ...] = (),
) -> CertidaoTcu:
    return CertidaoTcu(tipo, situacao, observacao, datas, processos, None)


def tcu(*certidoes: CertidaoTcu, encontrado: bool = True) -> Obtido[RespostaTcu]:
    tipos = {c.tipo for c in certidoes}
    completas = (*certidoes, *(certidao(t) for t in TipoCertidaoTcu if t not in tipos))
    evidencia = RefEvidencia(9, "tcu_consolidada", "b" * 64, datetime(2026, 10, 1, tzinfo=UTC))
    return Obtido(RespostaTcu(CNPJ, "ASSOCIACAO TESTE", encontrado, completas), evidencia)


def obs(**campos: Any) -> ObservacoesSancoes:
    return ObservacoesSancoes(consultado=CNPJ, matriz=campos.pop("matriz", None), **campos)


class TestCeisCnep:
    def test_sancao_vigente_e_restricao(self) -> None:
        resultado = verificar_ceis(obs(locais=locais(sancao())), CONTEXTO, REGRAS, LIMITES)
        assert resultado.estado is Estado.RESTRICAO

    @pytest.mark.parametrize(
        ("fim", "estado"),
        [(REF, Estado.RESTRICAO), (date(2026, 9, 30), Estado.OK), (None, Estado.RESTRICAO)],
    )
    def test_vigencia_pela_data_de_fim_inclusive(self, fim: date | None, estado: Estado) -> None:
        resultado = verificar_ceis(obs(locais=locais(sancao(data_fim=fim))), CONTEXTO, REGRAS, LIMITES)
        assert resultado.estado is estado

    def test_sancao_expirada_vira_historico(self) -> None:
        resultado = verificar_ceis(
            obs(locais=locais(sancao(data_fim=date(2021, 11, 18)))), CONTEXTO, REGRAS, LIMITES
        )
        assert resultado.estado is Estado.OK
        assert "Histórico" in resultado.mensagem

    def test_tcu_constam_registros_com_local_expirado_nao_e_divergencia(self) -> None:
        constam = certidao(
            TipoCertidaoTcu.CEIS, SituacaoCertidaoTcu.CONSTAM_REGISTROS, "sem prazo (18/11/2021)"
        )
        observacoes = obs(locais=locais(sancao(data_fim=date(2021, 11, 18))), tcu={CNPJ: tcu(constam)})
        assert verificar_ceis(observacoes, CONTEXTO, REGRAS, LIMITES).estado is Estado.OK

    @pytest.mark.parametrize(
        ("observacao", "datas", "estado"),
        [
            ("com prazo (18/11/2021)", (date(2021, 11, 18),), Estado.OK),
            ("com prazo (02/06/2029)", (date(2029, 6, 2),), Estado.RESTRICAO),
            ("sem prazo (Sem informação)", (), Estado.RESTRICAO),
            ("a (18/11/2021)<br/>b (Sem informação)", (date(2021, 11, 18),), Estado.RESTRICAO),
        ],
    )
    def test_registro_so_no_tcu_depende_das_datas_legiveis(
        self, observacao: str, datas: tuple[date, ...], estado: Estado
    ) -> None:
        constam = certidao(TipoCertidaoTcu.CEIS, SituacaoCertidaoTcu.CONSTAM_REGISTROS, observacao, datas)
        resultado = verificar_ceis(obs(locais=locais(), tcu={CNPJ: tcu(constam)}), CONTEXTO, REGRAS, LIMITES)
        assert resultado.estado is estado

    def test_registros_duplicados_contam_uma_vez(self) -> None:
        resultado = verificar_ceis(
            obs(locais=locais(sancao(codigo_sancao="1"), sancao(codigo_sancao="2"))),
            CONTEXTO,
            REGRAS,
            LIMITES,
        )
        assert resultado.mensagem.startswith("1 registro(s)")

    @pytest.mark.parametrize(
        ("raiz", "estado"),
        [(Raiz.RESTRICAO, Estado.RESTRICAO), (Raiz.ALERTA, Estado.ALERTA), (Raiz.EXATO, Estado.OK)],
    )
    def test_sancao_em_outro_estabelecimento_segue_q20(self, raiz: Raiz, estado: Estado) -> None:
        regras = replace(REGRAS, raiz=raiz)
        resultado = verificar_ceis(obs(locais=locais(sancao(documento=OUTRO))), CONTEXTO, regras, LIMITES)
        assert resultado.estado is estado

    def test_sancao_na_matriz_sempre_conta(self) -> None:
        regras = replace(REGRAS, raiz=Raiz.EXATO)
        resultado = verificar_ceis(
            obs(matriz=MATRIZ, locais=locais(sancao(documento=MATRIZ))), CONTEXTO, regras, LIMITES
        )
        assert resultado.estado is Estado.RESTRICAO

    @pytest.mark.parametrize(
        ("regra", "estado"), [(CnepMulta.ALERTA, Estado.ALERTA), (CnepMulta.RESTRICAO, Estado.RESTRICAO)]
    )
    def test_multa_do_cnep_segue_q16(self, regra: CnepMulta, estado: Estado) -> None:
        multa = sancao(CadastroSancao.CNEP, categoria="Multa", data_fim=None, valor_multa=Decimal("1000.00"))
        resultado = verificar_cnep(
            obs(locais=locais(multa)), CONTEXTO, replace(REGRAS, cnep_multa=regra), LIMITES
        )
        assert resultado.estado is estado

    def test_base_vencida_e_sem_tcu_fica_indisponivel(self) -> None:
        resultado = verificar_ceis(
            obs(locais=locais(sancao(), data_base=date(2026, 9, 20))), CONTEXTO, REGRAS, LIMITES
        )
        assert resultado.estado is Estado.INDISPONIVEL

    def test_base_vencida_mas_tcu_responde(self) -> None:
        resultado = verificar_ceis(
            obs(locais=locais(data_base=date(2026, 9, 20)), tcu={CNPJ: tcu()}), CONTEXTO, REGRAS, LIMITES
        )
        assert resultado.estado is Estado.OK


class TestCepim:
    def test_registro_presente_e_restricao_mesmo_sem_datas(self) -> None:
        impedimento = sancao(
            CadastroSancao.CEPIM, data_inicio=None, data_fim=None, convenio="123", motivo="Omissão"
        )
        resultado = verificar_cepim(obs(locais=locais(impedimento)), CONTEXTO, REGRAS, LIMITES)
        assert resultado.estado is Estado.RESTRICAO
        assert "convênio 123" in resultado.mensagem

    def test_so_uniao_vira_alerta_em_parceria_municipal(self) -> None:
        impedimento = sancao(CadastroSancao.CEPIM, data_fim=None)
        regras = replace(REGRAS, cepim=CepimEsfera.SO_UNIAO)
        contexto = Contexto(REF, Esfera.MUNICIPIO)
        assert (
            verificar_cepim(obs(locais=locais(impedimento)), contexto, regras, LIMITES).estado
            is Estado.ALERTA
        )

    def test_sem_carga_fica_indisponivel(self) -> None:
        assert verificar_cepim(obs(), CONTEXTO, REGRAS, LIMITES).estado is Estado.INDISPONIVEL


def lista(
    lista_tcu: ListaTcu, *registros: RegistroListaTcu
) -> dict[ListaTcu, ConsultaLocal[RegistroListaTcu] | None]:
    return {lista_tcu: ConsultaLocal(carga(FONTES_CARGA[lista_tcu]), registros)}


def registro(lista_tcu: ListaTcu, **alteracoes: Any) -> RegistroListaTcu:
    base = RegistroListaTcu(
        lista_tcu, CNPJ, CNPJ[:8], "ASSOCIACAO TESTE", "024.778/2024-9", "1610/2025-PL", None, None, None
    )
    return replace(base, **alteracoes)


class TestTcuInidoneos:
    def test_tcu_constam_e_restricao(self) -> None:
        constam = certidao(
            TipoCertidaoTcu.INIDONEOS, SituacaoCertidaoTcu.CONSTAM_REGISTROS, "Data da Decisão: ..."
        )
        resultado = verificar_tcu_inidoneos(obs(tcu={CNPJ: tcu(constam)}), CONTEXTO, REGRAS, LIMITES)
        assert resultado.estado is Estado.RESTRICAO

    def test_lista_local_vigente_e_restricao_e_expirada_e_historico(self) -> None:
        vigente = registro(ListaTcu.INIDONEOS, data_final=date(2027, 1, 1))
        expirada = registro(ListaTcu.INIDONEOS, data_final=date(2020, 1, 1), processo="1")
        assert (
            verificar_tcu_inidoneos(
                obs(listas=lista(ListaTcu.INIDONEOS, vigente)), CONTEXTO, REGRAS, LIMITES
            ).estado
            is Estado.RESTRICAO
        )
        assert (
            verificar_tcu_inidoneos(
                obs(listas=lista(ListaTcu.INIDONEOS, expirada)), CONTEXTO, REGRAS, LIMITES
            ).estado
            is Estado.OK
        )

    def test_cnpj_fora_da_base_do_tcu_e_informativo(self) -> None:
        resultado = verificar_tcu_inidoneos(obs(tcu={CNPJ: tcu(encontrado=False)}), CONTEXTO, REGRAS, LIMITES)
        assert resultado.estado is Estado.OK
        assert "não consta na base do TCU" in resultado.mensagem

    def test_sem_nenhuma_fonte_fica_indisponivel(self) -> None:
        falha = Falha(MotivoFalha.TIMEOUT, "lento")
        assert (
            verificar_tcu_inidoneos(obs(tcu={CNPJ: falha}), CONTEXTO, REGRAS, LIMITES).estado
            is Estado.INDISPONIVEL
        )


class TestCnia:
    PROCESSO = "12345678901234567890"

    def _constam(self) -> Obtido[RespostaTcu]:
        return tcu(
            certidao(
                TipoCertidaoTcu.CNIA, SituacaoCertidaoTcu.CONSTAM_REGISTROS, "x", processos=(self.PROCESSO,)
            )
        )

    @pytest.mark.parametrize(
        ("fim", "estado"), [(date(2027, 1, 1), Estado.RESTRICAO), (date(2020, 1, 1), Estado.ALERTA)]
    )
    def test_vigencia_pela_proibicao_ligada_no_ceis(self, fim: date, estado: Estado) -> None:
        ligada = sancao(processo=self.PROCESSO, data_fim=fim)
        resultado = verificar_cnj_cnia(
            obs(locais=locais(ligada), tcu={CNPJ: self._constam()}), CONTEXTO, REGRAS
        )
        assert resultado.estado is estado

    def test_sem_ligacao_e_alerta_e_qualquer_registro_e_restricao(self) -> None:
        observacoes = obs(locais=locais(), tcu={CNPJ: self._constam()})
        assert verificar_cnj_cnia(observacoes, CONTEXTO, REGRAS).estado is Estado.ALERTA
        regras = replace(REGRAS, cnia=Cnia.QUALQUER_REGISTRO)
        assert verificar_cnj_cnia(observacoes, CONTEXTO, regras).estado is Estado.RESTRICAO

    def test_nao_suportado_fica_indisponivel(self) -> None:
        resposta = tcu(certidao(TipoCertidaoTcu.CNIA, SituacaoCertidaoTcu.NAO_SUPORTADO))
        assert verificar_cnj_cnia(obs(tcu={CNPJ: resposta}), CONTEXTO, REGRAS).estado is Estado.INDISPONIVEL


class TestContasIrregulares:
    @pytest.mark.parametrize(
        ("transito", "estado"),
        [
            (date(2018, 10, 1), Estado.ALERTA),
            (date(2018, 9, 30), Estado.OK),
            (date(2026, 10, 1), Estado.ALERTA),
        ],
    )
    def test_janela_de_8_anos(self, transito: date, estado: Estado) -> None:
        itens = lista(
            ListaTcu.CONTAS_IRREGULARES, registro(ListaTcu.CONTAS_IRREGULARES, data_transito=transito)
        )
        resultado = verificar_tcu_contas_irregulares(obs(listas=itens), CONTEXTO, REGRAS, LIMITES)
        assert resultado.estado is estado

    def test_sem_carga_fica_indisponivel(self) -> None:
        assert (
            verificar_tcu_contas_irregulares(obs(), CONTEXTO, REGRAS, LIMITES).estado is Estado.INDISPONIVEL
        )
