import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from validador_osc.dominio.coleta import RefEvidencia
from validador_osc.dominio.evidencias import RespostaBruta, RespostaGuardada, ResultadoResposta


@dataclass
class EvidenciasEmMemoria:
    gravadas: list[tuple[RespostaBruta, RefEvidencia]] = field(default_factory=list)

    async def gravar(self, resposta: RespostaBruta) -> RefEvidencia:
        sha256 = hashlib.sha256(resposta.corpo).hexdigest() if resposta.corpo is not None else None
        ref = RefEvidencia(len(self.gravadas) + 1, resposta.fonte, sha256, resposta.recebida_em)
        self.gravadas.append((resposta, ref))
        return ref

    async def buscar_recente(
        self, fonte: str, chave: str, validade: timedelta, agora: datetime
    ) -> RespostaGuardada | None:
        candidatas = [
            (resposta, ref)
            for resposta, ref in self.gravadas
            if resposta.fonte == fonte
            and resposta.chave == chave
            and resposta.resultado is not ResultadoResposta.FALHA
            and resposta.recebida_em >= agora - validade
        ]
        if not candidatas:
            return None
        resposta, ref = max(candidatas, key=lambda par: par[0].recebida_em)
        return RespostaGuardada(
            resposta.resultado,
            resposta.corpo,
            RefEvidencia(ref.id, ref.fonte, ref.sha256, ref.recebida_em, de_cache=True),
        )

    def semear(
        self,
        fonte: str,
        url: str,
        chave: str,
        resultado: ResultadoResposta,
        corpo: bytes | None,
        recebida_em: datetime,
    ) -> None:
        asyncio.run(
            self.gravar(
                RespostaBruta(
                    fonte=fonte,
                    chave=chave,
                    url=url,
                    resultado=resultado,
                    recebida_em=recebida_em,
                    duracao_ms=10,
                    tentativas=1,
                    http_status=404 if resultado is ResultadoResposta.NAO_ENCONTRADO else 200,
                    corpo=corpo,
                )
            )
        )

    def de(self, fonte: str) -> list[RespostaBruta]:
        return [resposta for resposta, _ in self.gravadas if resposta.fonte == fonte]
