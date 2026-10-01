from sqlalchemy.ext.asyncio import AsyncEngine

from validador_osc.persistencia.banco import banco_pronto


async def verificar_prontidao(engine: AsyncEngine) -> bool:
    try:
        return await banco_pronto(engine)
    except Exception:
        return False
