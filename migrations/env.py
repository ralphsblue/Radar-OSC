from alembic import context

from validador_osc.config import obter_configuracao
from validador_osc.persistencia.banco import criar_engine
from validador_osc.persistencia.modelos import Base

configuracao_alembic = context.config
metadados = Base.metadata


def _url() -> str:
    url = configuracao_alembic.get_main_option("sqlalchemy.url")
    return url or obter_configuracao().url_banco


def executar_offline() -> None:
    context.configure(url=_url(), target_metadata=metadados, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def executar_online() -> None:
    engine = criar_engine(_url())
    with engine.connect() as conexao:
        context.configure(connection=conexao, target_metadata=metadados, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    executar_offline()
else:
    executar_online()
