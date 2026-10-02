# Fixtures da BrasilAPI

Respostas reais de `https://brasilapi.com.br/api/cnpj/v1/{cnpj}`, usadas por `tests/contrato/test_normalizacao_brasilapi.py`, `tests/unit/test_fonte_brasilapi.py` e pelo replay dos testes E2E (`tests/e2e/replay.py`, que devolve 404 genérico para CNPJ sem fixture).

## Origem e fidelidade

As respostas vêm da Fase 0 (`fase0/brasilapi/respostas/brasilapi_<caso>_<cnpj>.json` e, para o erro 500, `fase0/brasilapi/respostas/falhas/`).
Esses arquivos guardam o corpo já decodificado dentro de um envelope `{"caso", "url", "consultado_em", "http", "ms", "headers_relevantes", "corpo"}`.
Ao contrário da coleta do OpenCNPJ, a Fase 0 da BrasilAPI não gravou o sha256 dos bytes originais.
A conferência foi feita pelo `etag` que a BrasilAPI (Next.js na Vercel) devolve e que ficou gravado em `headers_relevantes`.
Esse `etag` é o FNV-1a de 52 bits do corpo seguido do tamanho do corpo, os dois em base 36 (`generateETag` do Next.js).
Cada fixture foi regravada com `json.dumps(corpo, ensure_ascii=False, separators=(",", ":"))` em UTF-8 e só foi aceita quando o `etag` recalculado sobre esse texto conferiu com o gravado.
Ou seja, os arquivos são byte a byte o corpo HTTP que a BrasilAPI devolveu (JSON compacto, UTF-8, sem quebra de linha final).

Respostas sem `etag` (o 504 do Cloudflare) não puderam ser conferidas e por isso não viraram fixture; os testes usam um 504 sintético com `retry-after: 120`.

O QSA da BrasilAPI vem mascarado (`cnpj_cpf_do_socio` e `cpf_representante_legal` no formato `***123456**`); nenhuma fixture contém CPF completo.

## Arquivos

| Arquivo | URL | Coletado em (UTC) | HTTP | etag | sha256 | Caso |
|---|---|---|---|---|---|---|
| `19131243000197.json` | `/19131243000197` | 2026-10-01 01:05:41 | 200 | `149fsjaqt3b2al` | `721473356287deb74079289cea9074a622362a7fd41791be71dd1199b584b00a` | T1, Open Knowledge Brasil, associação ativa |
| `00000000000191.json` | `/00000000000191` | 2026-10-01 01:05:55 | 200 | `zei90603o5gld` | `f4c55ba5ba3910bfffe1c643250c527d0b3b17732153c9b4fc0962adbeccd909` | T2, Banco do Brasil, natureza 2038, QSA grande |
| `08942107000160.json` | `/08942107000160` | 2026-10-01 01:22:58 | 200 | `vm27nu0myo386` | `cfd4a0b87127c5c5eab779a3462d68cee4800285bc480be17025fdcdcbff6a7c` | T4, associação baixada com motivo 1 |
| `62779145000270.json` | `/62779145000270` | 2026-10-01 01:38:00 | 200 | `je2t6878mr2e4` | `24ad53de3d8f69d88b1a64700181954d36cd73b26b22c64bb9ccf1937a474b21` | T7, filial ativa (`identificador_matriz_filial` 2) |
| `62779145000190.json` | `/62779145000190` | 2026-10-01 01:07:29 | 200 | `6zf4fxb0nu369` | `4e20adc4e9ac5db949c9a866c41177cfe272a6a605ad4206f89d9c8269c21c3f` | T7m, matriz da filial acima, nome fantasia vazio |
| `04955882000523.json` | `/04955882000523` | 2026-10-01 02:06:01 | 200 | `b21bgj1w7n1xi` | `c31e91566839a595ba52aafba7615d20f28b8ad889b9f4de6557c5735a4b513a` | T7b, filial baixada com matriz ativa |
| `04955882000108.json` | `/04955882000108` | 2026-10-01 02:19:55 | 200 | `vutre8gdye2f2` | `0ec02507a6bc5f2469782ad073819c0afa242386e6a6b6cf16c2b2359e1ec946` | T7bm, Instituto GRPCOM, `data_situacao_cadastral` nula |
| `65478551000100.json` | `/65478551000100` | 2026-10-01 01:59:41 | 200 | `ty6qut5nun2tx` | `6234eb21bb2636449e4eee8ba4968d9cef9cc21382b70edd2913c5691d2d87e1` | E1, associação aberta em 2026-02-03 |
| `00108217000110.json` | `/00108217000110` | 2026-10-01 02:14:13 | 200 | `lft1mz8xmy20m` | `fa390756ecbc6fa2af34552ea2bdee9715fb33571918cd47a6c898d856d96620` | E2, organização religiosa (3220), sem CNAE secundário |
| `04311762000160.json` | `/04311762000160` | 2026-10-01 02:14:25 | 200 | `z9wzpz4j952vn` | `c4d93af3548521005090d4939b67a6de3e07425c06e722a89ec4d27aecee1df8` | E3, cooperativa (2143), `cnae_fiscal` 220903 sem o zero |
| `00000000E08G12.json` | `/00000000E08G12` | 2026-10-01 02:48:21 | 200 | `6s8tyie78tfu0` | `256b66f1cfd1f232f65a18cb2c2fcdb93ded2d799f844f5b3498d49875559511` | T5r, primeiro CNPJ alfanumérico real (filial do Banco do Brasil) |
| `404_12ABC34501DE35.json` | `/12ABC34501DE35` | 2026-10-01 01:06:52 | 404 | `13vk89z7g1p2n` | `c726a7ea3208ed1fc5a6d361dab5acc440dda8c913f4990a991a3c1da261164d` | T5, exemplo alfanumérico oficial, inexistente |
| `400_19131243000198.json` | `/19131243000198` | 2026-10-01 01:06:23 | 400 | `gciiwp3ofh2l` | `d2848e6f2584d565f2d34b94124c16d2edc3ba1c1d8081776307d7f488cee337` | T3b, DV inválido |
| `500_65478551000100.json` | `/65478551000100` | 2026-10-01 01:31:30 | 500 | `1685ghjofao2l` | `77dbe48916c268092a412b2a6aa0042d135f61cd42ed41143b7856fb119f1557` | Minha Receita fora: `Request failed with status code 503` |

A coluna sha256 é o hash dos bytes do arquivo, calculado na regravação.

## Como renovar

Prefira o comando de gravação de fixtures do projeto (T13) quando existir.
Ao trocar um arquivo, mantenha os bytes exatos da resposta HTTP e atualize esta tabela e os valores esperados nos testes de contrato.
