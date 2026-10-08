from collections.abc import Callable
from datetime import date, timedelta

import pytest

from tests.unit.fabricas import DATA_REFERENCIA, EVIDENCIA, coleta_obtida, fonte_esperada, obtido
from validador_osc.dominio.coleta import Falha, MotivoFalha, NaoEncontrado
from validador_osc.dominio.consulta import Contexto, Esfera
from validador_osc.dominio.resultado import Estado, ResultadoVerificacao, TipoVerificacao
from validador_osc.dominio.tipos import SituacaoCadastral
from validador_osc.regras.catalogo import (
    CNAE,
    NATUREZA,
    RELIGIOSA,
    SITUACAO,
    TEMPO,
)
from validador_osc.regras.entidade import Entidade, SituacaoMatriz
from validador_osc.regras.tabelas import (
    AvaliacaoCnae,
    RegraNatureza,
    avaliar_cnaes,
    carregar_tabelas,
    formatar_cnae,
)
from validador_osc.regras.verificacoes.cadastro import (
    CadastroObtido,
    anos_completos,
    verificar_natureza,
    verificar_situacao,
    verificar_tempo,
)
from validador_osc.regras.verificacoes.cnae import verificar_cnae, verificar_religiosa
from validador_osc.regras.verificacoes.estabelecimento import verificar_estabelecimento

TABELAS = carregar_tabelas()
CONTEXTO = Contexto(data_referencia=DATA_REFERENCIA)
NATUREZA_ASSOCIACAO = 3999
NATUREZA_RELIGIOSA = 3220
CNAE_ALTA = "9430800"
CNAE_ALTA_SOCIAL = "8800600"
CNAE_MEDIA = "9499500"
CNAE_BAIXA = "4711302"
CNAE_RELIGIOSO = "9491000"


def avaliacao(
    principal: str, secundarios: tuple[str, ...] = (), natureza: int | None = NATUREZA_ASSOCIACAO
) -> AvaliacaoCnae:
    return avaliar_cnaes(TABELAS.cnae, natureza, principal, secundarios)


def tempo(
    inicio: date | None, referencia: date = DATA_REFERENCIA, esfera: Esfera | None = None
) -> ResultadoVerificacao:
    return verificar_tempo(obtido(data_inicio=inicio), Contexto(referencia, esfera))


class TestSituacao:
    def test_ativa_com_base_recente_e_ok(self) -> None:
        resultado = verificar_situacao(coleta_obtida(), CONTEXTO)
        assert resultado.definicao is SITUACAO
        assert resultado.estado is Estado.OK
        assert resultado.mensagem == "Situação ATIVA desde 03/10/2013."
        assert resultado.fontes == (fonte_esperada(),)

    @pytest.mark.parametrize(
        "situacao", [s for s in SituacaoCadastral if s is not SituacaoCadastral.ATIVA], ids=lambda s: s.name
    )
    def test_qualquer_situacao_nao_ativa_e_restricao(self, situacao: SituacaoCadastral) -> None:
        coleta = coleta_obtida(
            situacao=situacao, situacao_data=date(2012, 1, 4), motivo_descricao="EXTINCAO POR ENCERRAMENTO"
        )
        resultado = verificar_situacao(coleta, CONTEXTO)
        assert resultado.estado is Estado.RESTRICAO
        assert f"Situação {situacao.name} desde 04/01/2012." in resultado.mensagem
        assert "Motivo: EXTINCAO POR ENCERRAMENTO." in resultado.mensagem
        assert "13.019/2014" in resultado.mensagem
        assert resultado.fontes == (fonte_esperada(),)

    def test_nao_ativa_sem_motivo_e_sem_data(self) -> None:
        coleta = coleta_obtida(situacao=SituacaoCadastral.BAIXADA, situacao_data=None, motivo_descricao=None)
        resultado = verificar_situacao(coleta, CONTEXTO)
        assert resultado.estado is Estado.RESTRICAO
        assert resultado.mensagem.startswith("Situação BAIXADA. A Lei")
        assert "desde" not in resultado.mensagem
        assert "Motivo" not in resultado.mensagem

    def test_ativa_sem_data_nao_menciona_desde(self) -> None:
        resultado = verificar_situacao(coleta_obtida(situacao_data=None), CONTEXTO)
        assert resultado.estado is Estado.OK
        assert resultado.mensagem == "Situação ATIVA."

    def test_nao_ativa_com_base_antiga_continua_restricao(self) -> None:
        coleta = coleta_obtida(situacao=SituacaoCadastral.INAPTA, data_base=date(2025, 1, 1))
        assert verificar_situacao(coleta, CONTEXTO).estado is Estado.RESTRICAO

    def test_base_com_exatamente_60_dias_e_ok(self) -> None:
        coleta = coleta_obtida(data_base=date(2026, 8, 2))
        assert verificar_situacao(coleta, CONTEXTO).estado is Estado.OK

    def test_base_com_mais_de_60_dias_e_alerta(self) -> None:
        coleta = coleta_obtida(data_base=date(2026, 8, 1))
        resultado = verificar_situacao(coleta, CONTEXTO)
        assert resultado.estado is Estado.ALERTA
        assert "01/08/2026" in resultado.mensagem
        assert "Receita" in resultado.mensagem
        assert resultado.fontes == (fonte_esperada(date(2026, 8, 1)),)

    def test_base_sem_data_e_ok(self) -> None:
        coleta = coleta_obtida(data_base=None)
        resultado = verificar_situacao(coleta, CONTEXTO)
        assert resultado.estado is Estado.OK
        assert resultado.fontes[0].data_base is None

    def test_nao_encontrado_e_indisponivel(self) -> None:
        resultado = verificar_situacao(NaoEncontrado(EVIDENCIA), CONTEXTO)
        assert resultado.estado is Estado.INDISPONIVEL
        assert resultado.situacao == "NAO_ENCONTRADO"
        assert "não encontrado" in resultado.mensagem

    @pytest.mark.parametrize("motivo", list(MotivoFalha), ids=str)
    def test_falha_e_indisponivel_com_motivo(self, motivo: MotivoFalha) -> None:
        resultado = verificar_situacao(Falha(motivo, "detalhe técnico"), CONTEXTO)
        assert resultado.estado is Estado.INDISPONIVEL
        assert resultado.situacao == "FONTE_INDISPONIVEL"
        assert f"({motivo})" in resultado.mensagem
        assert "detalhe técnico" not in resultado.mensagem


class TestNatureza:
    @pytest.mark.parametrize(
        ("descricao", "codigo", "regra", "estado"),
        [
            ("Associação Privada", 3999, RegraNatureza.ELEGIVEL, Estado.OK),
            ("Fundação Privada", 3069, RegraNatureza.ELEGIVEL, Estado.OK),
            ("Organização Religiosa", 3220, RegraNatureza.ELEGIVEL_COM_ALERTA_RELIGIOSO, Estado.OK),
            ("Cooperativa", 2143, RegraNatureza.REVISAO_MANUAL, Estado.ALERTA),
            ("Sociedade Empresária Limitada", 2062, RegraNatureza.NAO_ELEGIVEL, Estado.RESTRICAO),
        ],
    )
    def test_cada_regra_pela_descricao(
        self, descricao: str, codigo: int, regra: RegraNatureza, estado: Estado
    ) -> None:
        resultado = verificar_natureza(obtido(natureza_descricao=descricao), TABELAS.natureza)
        assert resultado.definicao is NATUREZA
        assert resultado.estado is estado
        assert resultado.achados[0].dados == {"codigo": codigo, "regra": regra.value}
        assert TABELAS.natureza.naturezas[codigo].codigo_formatado in resultado.mensagem
        assert resultado.fontes == (fonte_esperada(),)

    @pytest.mark.parametrize("codigo", sorted(TABELAS.natureza.naturezas))
    def test_toda_a_tabela_pelo_codigo(self, codigo: int) -> None:
        esperado = {
            RegraNatureza.ELEGIVEL: Estado.OK,
            RegraNatureza.ELEGIVEL_COM_ALERTA_RELIGIOSO: Estado.OK,
            RegraNatureza.REVISAO_MANUAL: Estado.ALERTA,
            RegraNatureza.NAO_ELEGIVEL: Estado.RESTRICAO,
        }
        regra = TABELAS.natureza.naturezas[codigo].regra
        resultado = verificar_natureza(
            obtido(natureza_codigo=codigo, natureza_descricao=None), TABELAS.natureza
        )
        assert resultado.estado is esperado[regra]

    def test_revisao_manual_traz_justificativa(self) -> None:
        resultado = verificar_natureza(obtido(natureza_descricao="Cooperativa"), TABELAS.natureza)
        assert "revisão manual" in resultado.mensagem
        assert TABELAS.natureza.naturezas[2143].justificativa in resultado.mensagem

    @pytest.mark.parametrize(
        ("codigo", "descricao", "trecho"),
        [
            (None, "Natureza Que Não Existe", "(Natureza Que Não Existe)"),
            (None, None, "(não informada)"),
            (9999, "Inventada", "(Inventada)"),
        ],
    )
    def test_desconhecida_e_alerta_nunca_restricao(
        self, codigo: int | None, descricao: str | None, trecho: str
    ) -> None:
        resultado = verificar_natureza(
            obtido(natureza_codigo=codigo, natureza_descricao=descricao), TABELAS.natureza
        )
        assert resultado.estado is Estado.ALERTA
        assert trecho in resultado.mensagem
        assert resultado.achados == ()


class TestAnosCompletos:
    @pytest.mark.parametrize(
        ("inicio", "referencia", "anos"),
        [
            (date(2025, 10, 2), date(2026, 10, 1), 0),
            (date(2025, 10, 1), date(2026, 10, 1), 1),
            (date(2026, 10, 1), date(2026, 10, 1), 0),
            (date(2024, 2, 29), date(2025, 2, 27), 0),
            (date(2024, 2, 29), date(2025, 2, 28), 1),
            (date(2024, 2, 29), date(2025, 3, 1), 1),
            (date(2024, 2, 29), date(2028, 2, 28), 3),
            (date(2024, 2, 29), date(2028, 2, 29), 4),
            (date(2023, 2, 28), date(2024, 2, 28), 1),
            (date(2023, 3, 1), date(2024, 2, 29), 0),
        ],
    )
    def test_aniversario_conta(self, inicio: date, referencia: date, anos: int) -> None:
        assert anos_completos(inicio, referencia) == anos


class TestTempo:
    @pytest.mark.parametrize(
        ("esfera", "prazo"), [(Esfera.MUNICIPIO, 1), (Esfera.ESTADO, 2), (Esfera.UNIAO, 3)]
    )
    def test_fronteira_com_esfera(self, esfera: Esfera, prazo: int) -> None:
        no_dia = date(DATA_REFERENCIA.year - prazo, DATA_REFERENCIA.month, DATA_REFERENCIA.day)
        vespera = no_dia + timedelta(days=1)
        assert tempo(no_dia, esfera=esfera).estado is Estado.OK
        resultado = tempo(vespera, esfera=esfera)
        assert resultado.estado is Estado.ALERTA
        assert "art. 33, V, a" in resultado.mensagem
        assert "reduzir o prazo" in resultado.mensagem

    @pytest.mark.parametrize(
        ("inicio", "estado", "atende"),
        [
            (date(2025, 10, 2), Estado.ALERTA, (False, False, False)),
            (date(2025, 10, 1), Estado.ALERTA, (True, False, False)),
            (date(2024, 10, 2), Estado.ALERTA, (True, False, False)),
            (date(2024, 10, 1), Estado.ALERTA, (True, True, False)),
            (date(2023, 10, 2), Estado.ALERTA, (True, True, False)),
            (date(2023, 10, 1), Estado.OK, (True, True, True)),
        ],
    )
    def test_fronteiras_sem_esfera(self, inicio: date, estado: Estado, atende: tuple[bool, ...]) -> None:
        resultado = tempo(inicio)
        assert resultado.definicao is TEMPO
        assert resultado.estado is estado
        assert [a.dados for a in resultado.achados] == [
            {"esfera": "municipio", "prazo_anos": 1, "atende": atende[0]},
            {"esfera": "estado", "prazo_anos": 2, "atende": atende[1]},
            {"esfera": "uniao", "prazo_anos": 3, "atende": atende[2]},
        ]
        assert resultado.fontes == (fonte_esperada(),)

    def test_mensagem_sem_esfera_e_sem_prazo_atingido(self) -> None:
        assert tempo(date(2025, 10, 2)).mensagem == (
            "0 anos completos desde 02/10/2025: ainda não atinge o prazo mínimo de 1 ano para "
            "nenhuma esfera (art. 33, V, a)."
        )

    def test_mensagem_sem_esfera_com_um_ano(self) -> None:
        assert tempo(date(2025, 10, 1)).mensagem == (
            "1 ano completo desde 01/10/2025: atende o prazo para municípios; o prazo é de 2 anos para "
            "estados e Distrito Federal e de 3 anos para a União (art. 33, V, a)."
        )

    def test_mensagem_sem_esfera_com_dois_anos(self) -> None:
        assert tempo(date(2024, 10, 1)).mensagem == (
            "2 anos completos desde 01/10/2024: atende o prazo para municípios, estados e Distrito Federal; "
            "o prazo é de 3 anos para a União (art. 33, V, a)."
        )

    def test_mensagem_sem_esfera_com_todos_os_prazos(self) -> None:
        assert tempo(date(2013, 10, 3)).mensagem == (
            "12 anos completos desde 03/10/2013: atende o prazo para municípios, estados e a União."
        )

    def test_mensagens_com_esfera_no_singular_e_no_plural(self) -> None:
        assert tempo(date(2025, 10, 1), esfera=Esfera.MUNICIPIO).mensagem == (
            "1 ano completo desde 01/10/2025: atende o prazo de 1 ano exigido para municípios."
        )
        assert tempo(date(2025, 10, 1), esfera=Esfera.UNIAO).mensagem.startswith(
            "1 ano completo desde 01/10/2025: não atende o prazo de 3 anos exigido para a União "
            "(art. 33, V, a)."
        )
        assert tempo(date(2024, 10, 1), esfera=Esfera.ESTADO).mensagem == (
            "2 anos completos desde 01/10/2024: atende o prazo de 2 anos exigido para "
            "estados e Distrito Federal."
        )

    def test_29_de_fevereiro(self) -> None:
        inicio = date(2025, 2, 28)
        assert tempo(date(2024, 2, 29), date(2025, 2, 27), Esfera.MUNICIPIO).estado is Estado.ALERTA
        assert tempo(date(2024, 2, 29), inicio, Esfera.MUNICIPIO).estado is Estado.OK
        assert tempo(date(2024, 2, 29), date(2028, 2, 28), Esfera.UNIAO).estado is Estado.OK
        assert tempo(date(2024, 2, 29), date(2028, 2, 28)).mensagem.startswith("3 anos completos")

    def test_data_inicio_ausente_e_indisponivel(self) -> None:
        resultado = tempo(None, esfera=Esfera.UNIAO)
        assert resultado.estado is Estado.INDISPONIVEL
        assert resultado.achados == ()
        assert resultado.fontes == (fonte_esperada(),)


class TestCnae:
    def test_sem_cnae_principal_e_indisponivel(self) -> None:
        resultado = verificar_cnae(obtido(cnae_principal=None), TABELAS.cnae, None)
        assert resultado.definicao is CNAE
        assert resultado.estado is Estado.INDISPONIVEL
        assert resultado.fontes == (fonte_esperada(),)

    @pytest.mark.parametrize(
        ("principal", "estado", "faixa", "rotulo"),
        [
            (CNAE_ALTA, Estado.OK, "ALTA", "Aderência alta"),
            (CNAE_MEDIA, Estado.OK, "MEDIA", "Aderência média"),
            (CNAE_BAIXA, Estado.ALERTA, "BAIXA", "Nenhuma atividade cadastrada"),
        ],
    )
    def test_faixas(self, principal: str, estado: Estado, faixa: str, rotulo: str) -> None:
        resultado = verificar_cnae(obtido(), TABELAS.cnae, avaliacao(principal))
        assert resultado.estado is estado
        assert resultado.situacao == faixa
        assert resultado.mensagem.startswith(rotulo)
        assert f"principal {formatar_cnae(principal)}" in resultado.mensagem

    def test_secundario_alta_vence_principal_baixa(self) -> None:
        resultado = verificar_cnae(obtido(), TABELAS.cnae, avaliacao(CNAE_BAIXA, (CNAE_ALTA_SOCIAL,)))
        assert resultado.estado is Estado.OK
        assert resultado.situacao == "ALTA"

    def test_achados_de_principal_e_secundarios(self) -> None:
        resultado = verificar_cnae(obtido(), TABELAS.cnae, avaliacao(CNAE_BAIXA, (CNAE_ALTA, CNAE_MEDIA)))
        resumo = [(a.tipo, a.dados["papel"], a.dados["codigo"], a.dados["faixa"]) for a in resultado.achados]
        assert resumo == [
            ("cnae", "principal", formatar_cnae(CNAE_BAIXA), "BAIXA"),
            ("cnae", "secundario", formatar_cnae(CNAE_ALTA), "ALTA"),
            ("cnae", "secundario", formatar_cnae(CNAE_MEDIA), "MEDIA"),
        ]
        assert resultado.achados[0].dados["descricao"] == TABELAS.cnae.estrutura.subclasses[CNAE_BAIXA]


class TestReligiosa:
    def test_sem_avaliacao_nao_se_aplica(self) -> None:
        resultado = verificar_religiosa(obtido(cnae_principal=None), None)
        assert resultado.definicao is RELIGIOSA
        assert resultado.estado is Estado.OK
        assert "Não se aplica" in resultado.mensagem

    def test_nao_religiosa_nao_se_aplica(self) -> None:
        resultado = verificar_religiosa(obtido(), avaliacao(CNAE_MEDIA))
        assert resultado.estado is Estado.OK
        assert "Não se aplica" in resultado.mensagem

    @pytest.mark.parametrize(
        ("natureza", "principal", "secundarios", "estado"),
        [
            (NATUREZA_RELIGIOSA, CNAE_RELIGIOSO, (), Estado.ALERTA),
            (NATUREZA_RELIGIOSA, CNAE_MEDIA, (), Estado.ALERTA),
            (NATUREZA_RELIGIOSA, CNAE_BAIXA, (CNAE_MEDIA,), Estado.ALERTA),
            (NATUREZA_RELIGIOSA, CNAE_ALTA, (), Estado.OK),
            (NATUREZA_RELIGIOSA, CNAE_RELIGIOSO, (CNAE_ALTA_SOCIAL,), Estado.OK),
            (NATUREZA_ASSOCIACAO, CNAE_RELIGIOSO, (), Estado.ALERTA),
            (NATUREZA_ASSOCIACAO, CNAE_RELIGIOSO, (CNAE_MEDIA,), Estado.ALERTA),
            (NATUREZA_ASSOCIACAO, CNAE_RELIGIOSO, (CNAE_ALTA_SOCIAL,), Estado.OK),
            (None, CNAE_RELIGIOSO, (), Estado.ALERTA),
        ],
    )
    def test_gatilho_religioso(
        self, natureza: int | None, principal: str, secundarios: tuple[str, ...], estado: Estado
    ) -> None:
        avaliada = avaliacao(principal, secundarios, natureza)
        assert avaliada.gatilho_religioso
        resultado = verificar_religiosa(obtido(), avaliada)
        assert resultado.estado is estado
        assert "religiosa" in resultado.mensagem
        assert "Não se aplica" not in resultado.mensagem
        assert resultado.fontes == (fonte_esperada(),)

    def test_cnae_religioso_so_como_secundario_nao_dispara(self) -> None:
        avaliada = avaliacao(CNAE_MEDIA, (CNAE_RELIGIOSO,))
        assert not avaliada.gatilho_religioso
        assert "Não se aplica" in verificar_religiosa(obtido(), avaliada).mensagem


def _variacoes() -> list[CadastroObtido]:
    variacoes: list[CadastroObtido] = []
    for principal in (CNAE_ALTA, CNAE_MEDIA, CNAE_BAIXA, CNAE_RELIGIOSO, None):
        for natureza in ("Associação Privada", "Organização Religiosa", "Sociedade Anônima Aberta", None):
            for inicio in (date(2026, 9, 30), date(2025, 10, 1), date(2024, 2, 29), date(1990, 1, 1), None):
                for matriz in (True, False):
                    variacoes.append(
                        obtido(
                            cnae_principal=principal,
                            natureza_descricao=natureza,
                            data_inicio=inicio,
                            matriz=matriz,
                        )
                    )
    return variacoes


def _avaliacao_de(item: CadastroObtido) -> AvaliacaoCnae | None:
    cadastro = item.cadastro
    if cadastro.cnae_principal is None:
        return None
    natureza = NATUREZA_RELIGIOSA if cadastro.natureza_descricao == "Organização Religiosa" else None
    return avaliacao(cadastro.cnae_principal, cadastro.cnaes_secundarios, natureza)


def _entidade(item: CadastroObtido) -> Entidade:
    if item.cadastro.matriz:
        return Entidade(item, item, SituacaoMatriz.CONSULTADA_E_MATRIZ, None)
    return Entidade(item, None, SituacaoMatriz.NAO_IDENTIFICADA, None)


type Verificacao = Callable[[CadastroObtido, Contexto], ResultadoVerificacao]

NAO_ELIMINATORIAS: dict[str, Verificacao] = {
    "estabelecimento": lambda item, _: verificar_estabelecimento(_entidade(item)),
    "cnae": lambda item, _: verificar_cnae(item, TABELAS.cnae, _avaliacao_de(item)),
    "religiosa": lambda item, _: verificar_religiosa(item, _avaliacao_de(item)),
    "tempo": verificar_tempo,
}


@pytest.mark.parametrize("nome", NAO_ELIMINATORIAS)
@pytest.mark.parametrize("esfera", [None, *Esfera])
def test_verificacao_alerta_ou_informativa_nunca_devolve_restricao(nome: str, esfera: Esfera | None) -> None:
    verificar = NAO_ELIMINATORIAS[nome]
    contexto = Contexto(DATA_REFERENCIA, esfera)
    estados: set[Estado] = set()
    for item in _variacoes():
        resultado = verificar(item, contexto)
        assert resultado.id == nome
        assert resultado.tipo in {TipoVerificacao.ALERTA, TipoVerificacao.INFORMATIVA}
        estados.add(resultado.estado)
    assert Estado.RESTRICAO not in estados
