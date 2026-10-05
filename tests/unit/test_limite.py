from validador_osc.api.limite import LimitePorCliente


class Relogio:
    def __init__(self) -> None:
        self.agora = 0.0

    def __call__(self) -> float:
        return self.agora


def test_bloqueia_acima_do_maximo_e_libera_depois_da_janela() -> None:
    relogio = Relogio()
    limite = LimitePorCliente(2, janela_s=60, relogio=relogio)
    assert limite.permitir("a")
    assert limite.permitir("a")
    assert not limite.permitir("a")
    assert limite.permitir("b")
    relogio.agora = 60
    assert limite.permitir("a")


def test_maximo_zero_desliga_o_limite() -> None:
    limite = LimitePorCliente(0)
    assert all(limite.permitir("a") for _ in range(100))
